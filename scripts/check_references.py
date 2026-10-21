#!/usr/bin/env python3
"""Check that the documentation's verifiable references exist in the code.

The docs describe code that lives in sibling repositories (deploy, platform,
sdk-python, ...). This script extracts the references a reader would copy and
checks each one against those checkouts:

  make     `make <target>` and `make -C <repo> <target>` against the Makefiles
  path     backticked paths into a sibling repository (`deploy/compose.yaml`,
           `go/cmd/gateway/web`, ...)
  env      environment variable names (KIONGA_*, MLAIOPS_*, OIDC_*, *_PORT,
           *_URL, ...) against every non-Markdown file in the siblings
  route    /api/v1/..., /auth/..., /internal/v1/... routes against the routes
           the Go control plane registers
  cli      `mlaiops <command> <subcommand>` against platform/go/cmd/cli and
           `kionga <command>` against the workspace CLI (workspace/workspace/kionga.py)
  sdk      mlaiops_sdk modules, exports, and MLAIOpsClient methods
  style    house style in prose: no em dashes and no banned filler words

Usage:
  python scripts/check_references.py [--root ..] [--docs docs]

--root is the workspace folder that holds every Kionga checkout side by side
(deploy/scripts/workspace.sh creates it). It defaults to the parent of this
repository. Exit status: 0 clean, 1 findings, 2 missing sibling checkouts.

Known false positives live in scripts/reference-allowlist.txt, one
`<category> <value>` per line with a comment saying why.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

DOCS_REPO = Path(__file__).resolve().parent.parent

# Repositories the checks read. `docs` resolves to this repository.
REPOS = (
    "agent-runtime",
    "contracts",
    "deploy",
    "pipeline-runner",
    "platform",
    "sdk-python",
    "serving",
    "trace-proxy",
    "workspace",
)
REQUIRED = ("deploy", "platform", "sdk-python")

# Directories never searched: VCS data, caches, generated output, vendored
# build contexts (platform/go/build/context is a copy of the gateway source),
# and legacy docs folders inside code repositories.
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "site", "_site",
    ".pytest_cache", ".ruff_cache", ".mypy_cache", ".tools.nosync", ".local-state",
    "artifacts", "build", "bin", "docs",
}
CORPUS_SUFFIXES = {
    ".go", ".py", ".sh", ".bash", ".yaml", ".yml", ".json", ".toml", ".tpl",
    ".tmpl", ".cfg", ".conf", ".ini", ".js", ".mjs", ".cjs", ".ts", ".html",
    ".example", ".env", ".service", ".txt", ".sql", ".ipynb",
}
CORPUS_NAMES = {"Makefile", "Dockerfile", "Caddyfile", "Containerfile"}
MAX_CORPUS_BYTES = 2_000_000


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    category: str
    value: str
    message: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: [{self.category}] {self.value}: {self.message}"


# --------------------------------------------------------------------------
# Markdown: split each page into code contexts and prose.
# --------------------------------------------------------------------------

FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})\s*([\w+-]*)")
INLINE_CODE = re.compile(r"(`+)(.+?)\1")


@dataclass
class Segment:
    """A piece of a page: inline code, a fenced-code line, or a prose line."""

    kind: str  # "inline", "block", "prose"
    text: str
    line: int
    lang: str = ""
    block_id: int = -1


def segments(markdown: str) -> list[Segment]:
    out: list[Segment] = []
    fence: str | None = None
    lang = ""
    block = 0
    for number, line in enumerate(markdown.splitlines(), start=1):
        match = FENCE.match(line)
        if fence is None and match:
            fence, lang = match.group(2), match.group(3).lower()
            block += 1
            continue
        if fence is not None:
            if line.strip().startswith(fence[0] * len(fence)) and line.strip().strip(fence[0]) == "":
                fence = None
                continue
            out.append(Segment("block", line, number, lang, block))
            continue
        for code in INLINE_CODE.finditer(line):
            out.append(Segment("inline", code.group(2).strip(), number))
        out.append(Segment("prose", INLINE_CODE.sub(" ", line), number))
    return out


def code_segments(page: list[Segment]) -> list[Segment]:
    return [s for s in page if s.kind in ("inline", "block")]


# --------------------------------------------------------------------------
# Facts read from the sibling repositories.
# --------------------------------------------------------------------------

MAKE_TARGET = re.compile(r"^([A-Za-z0-9_.%/-]+(?:[ \t]+[A-Za-z0-9_.%/-]+)*)[ \t]*::?(?!=)")


def make_targets(makefile: Path) -> set[str]:
    targets: set[str] = set()
    if not makefile.is_file():
        return targets
    for line in makefile.read_text(errors="replace").splitlines():
        if line.startswith(("\t", "#", " ")):
            continue
        match = MAKE_TARGET.match(line)
        if match:
            targets.update(t for t in match.group(1).split() if not t.startswith("."))
    return targets


def walk(root: Path):
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_dir():
                if entry.name not in SKIP_DIRS:
                    stack.append(entry)
            elif entry.is_file():
                yield entry


ENV_TOKEN = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b")
ROUTE_LITERAL = re.compile(r'\bHandle(?:Func)?\(\s*"(?:([A-Z]+) )?(/[^"]*)"')
AUTH_CASE = re.compile(r'case\s+"(/auth/[^"]*)"')
CLI_CASE = re.compile(r'case\s+"([a-z][\w-]*) ([a-z][\w-]*)"')
CLI_ARG1 = re.compile(r'os\.Args\[1\]\s*==\s*"([a-z][\w-]*)"')
CLI_ARG2 = re.compile(r'os\.Args\[2\]\s*==\s*"([a-z][\w-]*)"')


@dataclass
class Facts:
    root: Path
    docs_repo: Path = DOCS_REPO
    makefiles: dict[str, set[str]] = field(default_factory=dict)
    env: set[str] = field(default_factory=set)
    routes: list[tuple[str, list[str]]] = field(default_factory=list)
    cli: set[tuple[str, str]] = field(default_factory=set)
    kionga: dict[str, set[str]] = field(default_factory=dict)
    sdk: dict[str, "Module"] = field(default_factory=dict)
    top_level: set[str] = field(default_factory=set)

    def repo(self, name: str) -> Path:
        return self.docs_repo if name == "docs" else self.root / name


SUBPARSERS = re.compile(r"(\w+)\s*=\s*(\w+)\.add_subparsers\(")
ADD_PARSER = re.compile(r"(?:(\w+)\s*=\s*)?(\w+)\.add_parser\(\s*\"([\w-]+)\"")


def argparse_commands(source: str) -> dict[str, set[str]]:
    """Map each top-level argparse command to its subcommands (empty if none)."""
    owner = {group: parser for group, parser in SUBPARSERS.findall(source)}
    parser_name: dict[str, str] = {}
    commands: dict[str, set[str]] = {}
    for variable, group, name in ADD_PARSER.findall(source):
        if variable:
            parser_name[variable] = name
        parent = parser_name.get(owner.get(group, ""), "")
        if parent:
            commands.setdefault(parent, set()).add(name)
        else:
            commands.setdefault(name, set())
    return commands


@dataclass
class Signature:
    params: set[str]
    var_keyword: bool
    returns: str = ""  # SDK class name the call returns, when annotated


@dataclass
class Module:
    names: set[str]
    classes: dict[str, set[str]]
    functions: dict[str, Signature] = field(default_factory=dict)
    methods: dict[str, dict[str, Signature]] = field(default_factory=dict)


PYDANTIC_MEMBERS = {
    "model_dump", "model_dump_json", "model_validate", "model_validate_json",
    "model_copy", "model_fields", "model_json_schema",
}


def signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> Signature:
    args = node.args
    params = {a.arg for a in args.posonlyargs + args.args + args.kwonlyargs} - {"self", "cls"}
    returns = ""
    if node.returns is not None:
        returns = ast.unparse(node.returns).strip("'\"")
        returns = returns if returns.isidentifier() else ""
    return Signature(params, args.kwarg is not None, returns)


def parse_sdk_module(path: Path) -> Module:
    tree = ast.parse(path.read_text(), filename=str(path))
    module = Module(set(), {})
    names = module.names
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
            module.functions[node.name] = signature(node)
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
            members: set[str] = set()
            methods: dict[str, Signature] = {}
            fields: set[str] = set()
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    members.add(item.name)
                    methods[item.name] = signature(item)
                elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    members.add(item.target.id)
                    fields.add(item.target.id)
                elif isinstance(item, ast.Assign):
                    members.update(t.id for t in item.targets if isinstance(t, ast.Name))
            bases = {ast.unparse(base) for base in node.bases}
            if "__init__" not in methods:
                # Pydantic models and dataclasses take their fields as keywords;
                # an unknown base class may define its own constructor.
                known = bases <= {"BaseModel", "object"} or any(
                    "dataclass" in ast.unparse(d) for d in node.decorator_list)
                methods["__init__"] = Signature(fields, not known)
            if "BaseModel" in bases:
                members |= PYDANTIC_MEMBERS
            module.classes[node.name] = members
            module.methods[node.name] = methods
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update((alias.asname or alias.name).split(".")[0] for alias in node.names)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
                    # __all__ and lazy-export tables name importable symbols.
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        names.update(
                            e.value for e in node.value.elts
                            if isinstance(e, ast.Constant) and isinstance(e.value, str)
                        )
                    if isinstance(node.value, ast.Dict):
                        names.update(
                            k.value for k in node.value.keys
                            if isinstance(k, ast.Constant) and isinstance(k.value, str)
                        )
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return module


def load_facts(root: Path, docs_repo: Path = DOCS_REPO) -> Facts:
    facts = Facts(root, docs_repo)
    for name in REPOS + ("docs",):
        repo = facts.repo(name)
        facts.makefiles[name] = make_targets(repo / "Makefile")
        if name != "docs" and repo.is_dir():
            facts.top_level.update(p.name for p in repo.iterdir() if not p.name.startswith("."))

    for name in REPOS:
        repo = root / name
        if not repo.is_dir():
            continue
        for path in walk(repo):
            if path.suffix not in CORPUS_SUFFIXES and path.name not in CORPUS_NAMES \
                    and not path.name.startswith(("Dockerfile", ".env")):
                continue
            try:
                if path.stat().st_size > MAX_CORPUS_BYTES:
                    continue
                text = path.read_text(errors="replace")
            except OSError:
                continue
            facts.env.update(ENV_TOKEN.findall(text))
            if path.suffix == ".go" and not path.name.endswith("_test.go") and name == "platform":
                for method, route in ROUTE_LITERAL.findall(text):
                    facts.routes.append((method, route_segments(route)))
                for route in AUTH_CASE.findall(text):
                    facts.routes.append(("", route_segments(route)))

    cli_dir = root / "platform" / "go" / "cmd" / "cli"
    if cli_dir.is_dir():
        for path in sorted(cli_dir.glob("*.go")):
            if path.name.endswith("_test.go"):
                continue
            for line in path.read_text().splitlines():
                facts.cli.update(CLI_CASE.findall(line))
                first = CLI_ARG1.findall(line)
                for command in first:
                    facts.cli.update((command, sub) for sub in CLI_ARG2.findall(line))

    kionga = root / "workspace" / "workspace" / "kionga.py"
    if kionga.is_file():
        facts.kionga = argparse_commands(kionga.read_text())

    sdk = root / "sdk-python" / "mlaiops_sdk"
    if sdk.is_dir():
        for path in sorted(sdk.glob("*.py")):
            dotted = "mlaiops_sdk" if path.stem == "__init__" else f"mlaiops_sdk.{path.stem}"
            facts.sdk[dotted] = parse_sdk_module(path)
    return facts


# --------------------------------------------------------------------------
# Checks. Each takes one page and returns findings.
# --------------------------------------------------------------------------

def check_make(page: list[Segment], facts: Facts, rel: str) -> list[Finding]:
    found = []
    for seg in code_segments(page):
        for match in re.finditer(r"(?:^|[\s;&|(`])make((?:[ \t]+[^\s;&|#)]+)+)", seg.text):
            directory, targets = "", []
            tokens = match.group(1).split()
            i = 0
            while i < len(tokens):
                token = tokens[i]
                if token == "-C" and i + 1 < len(tokens):
                    directory, i = tokens[i + 1], i + 2
                    continue
                if token.startswith("-C"):
                    directory = token[2:]
                elif token.startswith("-") or "=" in token:
                    pass
                elif re.fullmatch(r"[a-z][\w.-]*", token):
                    targets.append(token)
                else:
                    break
                i += 1
            if re.search(r"[<{$]", directory):
                continue  # a placeholder such as `make -C <repo> build`
            repo = re.sub(r"^(\./|\.\./)+", "", directory).split("/")[0] if directory else ""
            for target in targets:
                if repo:
                    if repo not in facts.makefiles:
                        found.append(Finding(rel, seg.line, "make", f"make -C {directory} {target}",
                                             f"unknown repository '{repo}'"))
                    elif target not in facts.makefiles[repo]:
                        found.append(Finding(rel, seg.line, "make", f"make -C {directory} {target}",
                                             f"no target '{target}' in {repo}/Makefile"))
                elif not any(target in t for t in facts.makefiles.values()):
                    found.append(Finding(rel, seg.line, "make", f"make {target}",
                                         "no Makefile in the workspace defines this target"))
    return found


PLACEHOLDER = re.compile(r"[<{].*")


_TRACKED: dict[Path, set[str] | None] = {}


def tracked_paths(base: Path) -> set[str] | None:
    """Files and directories git tracks under `base`, or None when `base` is not
    a git checkout. Untracked build output and local files (`bin/`, `.env`)
    then fail the same way locally as in CI."""
    base = base.resolve()
    if base not in _TRACKED:
        _TRACKED[base] = None
        if (base / ".git").exists():
            try:
                result = subprocess.run(
                    ["git", "-C", str(base), "ls-files", "-z"],
                    capture_output=True, check=True, timeout=30,
                )
            except (OSError, subprocess.SubprocessError):
                return None
            paths: set[str] = set()
            for name in result.stdout.decode(errors="replace").split("\0"):
                if not name:
                    continue
                parts = name.split("/")
                paths.update("/".join(parts[:i]) for i in range(1, len(parts) + 1))
            _TRACKED[base] = paths
    return _TRACKED[base]


def path_exists(base: Path, path: str) -> bool:
    path = path.rstrip("/")
    path = PLACEHOLDER.sub("", path).rstrip("/")  # check the part before <id> or {id}
    if not path:
        return base.exists()
    tracked = tracked_paths(base)
    if tracked is None:
        if any(ch in path for ch in "*?["):
            return any(base.glob(path))
        return (base / path).exists()
    if any(ch in path for ch in "*?["):
        return any(fnmatch.fnmatchcase(name, path) for name in tracked)
    return path in tracked


def repo_path_tokens(text: str) -> list[str]:
    names = "|".join(re.escape(r) for r in REPOS + ("docs",))
    pattern = re.compile(r"(?<![\w/.:@~$-])(?:\.{1,2}/)*((?:%s)/[\w.*{}<>/-]*)" % names)
    return [m.group(1).rstrip(".,:;") for m in pattern.finditer(text)]


def check_paths(page: list[Segment], facts: Facts, rel: str) -> list[Finding]:
    found = []
    for seg in code_segments(page):
        for token in repo_path_tokens(seg.text):
            repo, _, rest = token.partition("/")
            if not facts.repo(repo).is_dir():
                continue
            if not path_exists(facts.repo(repo), rest):
                found.append(Finding(rel, seg.line, "path", token, f"does not exist in {repo}/"))
        # A whole inline span that is a repository-relative path without the
        # repository name (`go/cmd/gateway/web`): it must exist in some repo.
        if seg.kind == "inline" and re.fullmatch(r"(?:\./)?[\w.-]+(?:/[\w.*-]+)+/?", seg.text):
            path = seg.text.removeprefix("./")
            first = path.split("/")[0]
            if first in REPOS or first == "docs" or first not in facts.top_level:
                continue
            if not any(path_exists(facts.root / repo, path) for repo in REPOS):
                found.append(Finding(rel, seg.line, "path", path,
                                     "not found in any sibling repository"))
    return found


ENV_DOC = re.compile(r"(?<![\w$.-])[A-Z][A-Z0-9]*(?:_(?:[A-Z0-9]+|\*))*_(?:[A-Z0-9]+|\*)(?![\w-])")


def check_env(page: list[Segment], facts: Facts, rel: str) -> list[Finding]:
    found, seen = [], set()
    for seg in page:
        for name in ENV_DOC.findall(seg.text):
            if (name, seg.line) in seen:
                continue
            seen.add((name, seg.line))
            if "*" in name:
                pattern = re.compile("^" + re.escape(name).replace(r"\*", "[A-Z0-9_]*") + "$")
                ok = any(pattern.match(n) for n in facts.env)
            else:
                ok = name in facts.env
            if not ok:
                found.append(Finding(rel, seg.line, "env", name,
                                     "not referenced by code, compose, Helm, or scripts"))
    return found


def route_segments(route: str) -> list[str]:
    return [s for s in route.split("/") if s != ""]


ROUTE_DOC = re.compile(
    r"(?:\b(GET|POST|PUT|PATCH|DELETE|HEAD)\s+`?)?"
    r"((?:https?://[\w.:-]+|\$\{?\w+\}?|(?<![\w.:/-]))/(?:api/v1|api/openapi\.json|auth|internal/v1)\b[^\s`'\"),|]*)"
)
LOCAL_HOSTS = re.compile(r"^https?://(?:localhost|127\.0\.0\.1|gateway|kionga\.example\.com|[\w.-]*example\.(?:com|org))(?::\d+)?")


def wildcard(segment: str) -> bool:
    return bool(re.fullmatch(r"\{.*\}|<.*>|:\w+|\*|…|\.\.\.|\$\w+|\$\{\w+\}", segment))


def expand_optional(route: str) -> list[str]:
    """Expand `[...]` optional parts: /a[/b[/c]] -> /a, /a/b, /a/b/c."""
    start = route.find("[")
    if start < 0:
        return [route.replace("]", "")]
    depth, end = 0, len(route)
    for index in range(start, len(route)):
        depth += {"[": 1, "]": -1}.get(route[index], 0)
        if depth == 0:
            end = index
            break
    before, inner, after = route[:start], route[start + 1:end], route[end + 1:]
    return expand_optional(before + after) + expand_optional(before + inner + after)


def route_matches(doc: list[str], prefix: bool, registered: list[str]) -> bool:
    for index, reg in enumerate(registered):
        if reg.startswith("{") and reg.endswith("...}"):
            return True
        if index >= len(doc):
            return prefix
        if reg.startswith("{") or wildcard(doc[index]):
            continue
        if doc[index] != reg:
            return False
    return len(doc) == len(registered) or (prefix and len(doc) <= len(registered))


def check_route(method: str, route: str, facts: Facts, rel: str, line: int) -> Finding | None:
    prefix = route.endswith(("/", "*", "…", "..."))
    parts = route_segments(re.sub(r"(/\*|/…|/\.\.\.|…|\*)$", "", route))
    if not parts or parts == ["api"] or parts == ["api", "v1"] or parts == ["auth"]:
        return None
    candidates = [r for m, r in facts.routes if not method or not m or m == method]
    if any(route_matches(parts, prefix, r) for r in candidates):
        return None
    hint = "method not registered for this path" if any(
        route_matches(parts, prefix, r) for _, r in facts.routes) else "no matching route"
    return Finding(rel, line, "route", f"{method} {route}".strip(), f"{hint} in platform/go")


def check_routes(page: list[Segment], facts: Facts, rel: str) -> list[Finding]:
    found = []
    for seg in page:
        if seg.kind == "prose" and "/api/" not in seg.text and "/auth/" not in seg.text:
            continue
        for method, raw in ROUTE_DOC.findall(seg.text):
            if raw.startswith("http"):
                if not LOCAL_HOSTS.match(raw):
                    continue  # another service's API
                raw = "/" + raw.split("/", 3)[3]
            elif raw.startswith("$"):
                raw = raw[raw.index("/"):]  # "$MLAIOPS_URL/api/v1/..." names the gateway
            for route in expand_optional(re.split(r"[?#]", raw)[0].rstrip(".:;")):
                finding = check_route(method, route, facts, rel, seg.line)
                if finding:
                    found.append(finding)
    return found


CLI_LINE = re.compile(
    r"^(?:\$\s+)?(?:[A-Z_][A-Z0-9_]*=\S*\s+)*"
    r"(?:\./)?(bin/mlaiops-cli|mlaiops-cli|mlaiops|go run \./cmd/cli|go run \./go/cmd/cli|kionga)"
    r"(?:\s+(.*))?$"
)


def check_cli(page: list[Segment], facts: Facts, rel: str) -> list[Finding]:
    """`mlaiops ...` against platform/go/cmd/cli; `kionga ...` against the
    workspace CLI's argparse tree."""
    found = []
    mlaiops = {c for c, _ in facts.cli}
    for seg in code_segments(page):
        if seg.kind == "block" and seg.lang not in ("", "bash", "sh", "shell", "console", "text"):
            continue
        match = CLI_LINE.match(seg.text.strip())
        if not match or not match.group(2):
            continue
        words = re.split(r"\s+", match.group(2).strip())
        command, sub = words[0], words[1] if len(words) > 1 else ""
        if command.startswith(("-", "<", "#", "|", "[")):
            continue
        if sub.startswith(("-", "<", "|", "[", "#", "\\")):
            sub = ""
        if match.group(1) == "kionga":
            if not facts.kionga:
                continue
            if command not in facts.kionga:
                found.append(Finding(rel, seg.line, "cli", f"kionga {command}",
                                     "no such command in workspace/workspace/kionga.py"))
            elif sub and facts.kionga[command] and sub not in facts.kionga[command]:
                found.append(Finding(rel, seg.line, "cli", f"kionga {command} {sub}",
                                     "no such subcommand in workspace/workspace/kionga.py"))
            continue
        if command not in mlaiops:
            found.append(Finding(rel, seg.line, "cli", f"mlaiops {command}",
                                 "no such command in platform/go/cmd/cli"))
        elif sub and (command, sub) not in facts.cli:
            found.append(Finding(rel, seg.line, "cli", f"mlaiops {command} {sub}",
                                 "no such subcommand in platform/go/cmd/cli"))
    return found


SDK_DOTTED = re.compile(r"\bmlaiops_sdk(?:\.\w+)+")
SDK_FROM = re.compile(r"\bfrom\s+(mlaiops_sdk(?:\.\w+)*)\s+import\s+(\([^)]*\)|[^\n]+)")
# By convention the docs call an MLAIOpsClient instance `client`, sometimes in
# a later block than the one that constructs it.
DEFAULT_INSTANCES = {"client": "MLAIOpsClient"}


def resolve_sdk(dotted: str, facts: Facts) -> str | None:
    """Return None when the dotted name exists, else a reason."""
    parts = dotted.split(".")
    module = "mlaiops_sdk"
    i = 1
    while i < len(parts) and f"{module}.{parts[i]}" in facts.sdk:
        module, i = f"{module}.{parts[i]}", i + 1
    if i == len(parts):
        return None
    name = parts[i]
    mod = facts.sdk[module]
    if name not in mod.names:
        return f"'{name}' is not defined in {module}"
    if i + 1 < len(parts):
        cls = next((m.classes[name] for m in facts.sdk.values() if name in m.classes), None)
        if cls is not None and parts[i + 1] not in cls:
            return f"{name} has no member '{parts[i + 1]}'"
    return None


@dataclass
class SDKIndex:
    classes: dict[str, set[str]]
    methods: dict[str, dict[str, Signature]]
    functions: dict[str, Signature]


def sdk_index(facts: Facts) -> SDKIndex:
    index = SDKIndex({}, {}, {})
    for module in facts.sdk.values():
        index.classes.update(module.classes)
        index.methods.update(module.methods)
        index.functions.update(module.functions)
    return index


def parse_python(text: str) -> ast.Module | None:
    lines = text.splitlines()
    if any(line.lstrip().startswith(">>>") for line in lines):
        lines = [re.sub(r"^\s*(>>>|\.\.\.) ?", "", l) for l in lines
                 if l.lstrip().startswith((">>>", "..."))]
    source = textwrap.dedent("\n".join(lines))
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def check_call(call: ast.Call, sig: Signature, label: str) -> list[str]:
    if sig.var_keyword:
        return []
    return [f"{label}() has no parameter '{kw.arg}'"
            for kw in call.keywords if kw.arg and kw.arg not in sig.params]


def check_python_ast(tree: ast.Module, index: SDKIndex, instances: dict[str, str],
                     imported: set[str]) -> list[tuple[int, str, str]]:
    """Track SDK instances through assignments and check member access and
    keyword arguments. Returns (line offset, value, reason)."""
    problems: list[tuple[int, str, str]] = []

    def class_of(node: ast.AST) -> str:
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in index.classes:
                return func.id
            if isinstance(func, ast.Attribute):
                if func.attr in index.classes and ast.unparse(func.value).startswith("mlaiops_sdk"):
                    return func.attr
                owner = class_of(func.value) if not isinstance(func.value, ast.Name) \
                    else instances.get(func.value.id, "")
                sig = index.methods.get(owner, {}).get(func.attr)
                if sig and sig.returns in index.classes:
                    return sig.returns
            if isinstance(func, ast.Name) and func.id in index.functions:
                returns = index.functions[func.id].returns
                return returns if returns in index.classes else ""
        if isinstance(node, ast.Name):
            return instances.get(node.id, "")
        return ""

    nodes = sorted((n for n in ast.walk(tree) if hasattr(n, "lineno")),
                   key=lambda n: (n.lineno, n.col_offset))
    for node in nodes:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            cls = class_of(node.value)
            if cls:
                instances[node.targets[0].id] = cls
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                cls = class_of(item.context_expr)
                if cls and isinstance(item.optional_vars, ast.Name):
                    instances[item.optional_vars.id] = cls
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            cls = instances.get(node.value.id)
            if cls and node.attr not in index.classes[cls] and not node.attr.startswith("_"):
                problems.append((node.lineno, f"{node.value.id}.{node.attr}",
                                 f"{cls} has no member '{node.attr}'"))
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                cls = instances.get(func.value.id)
                sig = index.methods.get(cls or "", {}).get(func.attr)
                if sig:
                    for reason in check_call(node, sig, f"{cls}.{func.attr}"):
                        problems.append((node.lineno, f"{func.value.id}.{func.attr}", reason))
            elif isinstance(func, ast.Name) and func.id in imported:
                if func.id in index.classes:
                    sig = index.methods[func.id].get("__init__")
                else:
                    sig = index.functions.get(func.id)
                if sig:
                    for reason in check_call(node, sig, func.id):
                        problems.append((node.lineno, func.id, reason))
    return problems


def check_sdk(page: list[Segment], facts: Facts, rel: str) -> list[Finding]:
    if not facts.sdk:
        return []
    found = []
    index = sdk_index(facts)
    instances = dict(DEFAULT_INSTANCES)
    imported: set[str] = set()
    blocks: dict[int, list[Segment]] = {}
    for seg in code_segments(page):
        if seg.kind == "block":
            blocks.setdefault(seg.block_id, []).append(seg)
    units = [[s] for s in code_segments(page) if s.kind == "inline"] + list(blocks.values())
    units.sort(key=lambda u: u[0].line)
    for unit in units:
        if unit[0].kind == "block" and unit[0].lang not in ("python", "py", "pycon", "ipython", ""):
            continue
        text = "\n".join(s.text for s in unit)

        def line_of(offset: int) -> int:
            return unit[min(text.count("\n", 0, offset), len(unit) - 1)].line

        for match in SDK_DOTTED.finditer(text):
            reason = resolve_sdk(match.group(0), facts)
            if reason:
                found.append(Finding(rel, line_of(match.start()), "sdk", match.group(0), reason))
        for match in SDK_FROM.finditer(text):
            module = match.group(1)
            if module not in facts.sdk:
                continue  # SDK_DOTTED already reported the module
            names = match.group(2).split("#")[0].strip("() \n")
            for item in names.split(","):
                name = item.split(" as ")[0].strip()
                if not name.isidentifier():
                    continue
                imported.add(item.split(" as ")[-1].strip())
                if name not in facts.sdk[module].names and f"{module}.{name}" not in facts.sdk:
                    found.append(Finding(rel, line_of(match.start()), "sdk",
                                         f"from {module} import {name}",
                                         f"'{name}' is not defined in {module}"))
        if unit[0].kind == "inline" and "(" not in text:
            continue  # `client.py` is a file name, not attribute access
        tree = parse_python(text)
        if tree is None:
            continue
        for lineno, value, reason in check_python_ast(tree, index, instances, imported):
            found.append(Finding(rel, unit[min(lineno - 1, len(unit) - 1)].line, "sdk", value, reason))
    return sorted(found, key=lambda f: f.line)


# House style: no em dashes, and none of these words, in prose. Code (inline
# or fenced) is exempt so quoted UI strings and command output stay exact.
BANNED_WORDS = (
    "delve", "crucial", "robust", "comprehensive", "nuanced", "multifaceted",
    "furthermore", "moreover", "pivotal", "landscape", "tapestry", "underscore",
    "foster", "showcase", "intricate", "vibrant", "fundamental", "significant",
    "interplay",
)
BANNED = re.compile(r"\b(%s)\b" % "|".join(BANNED_WORDS), re.IGNORECASE)


def check_style(page: list[Segment], facts: Facts, rel: str) -> list[Finding]:
    found = []
    for seg in page:
        if seg.kind != "prose":
            continue
        if "\u2014" in seg.text:
            found.append(Finding(rel, seg.line, "style", "\u2014",
                                 "em dash; use a comma, colon, parentheses, or a period"))
        for word in BANNED.findall(seg.text):
            found.append(Finding(rel, seg.line, "style", word.lower(), "word not used in these docs"))
    return found


CHECKS = {
    "make": check_make,
    "path": check_paths,
    "env": check_env,
    "route": check_routes,
    "cli": check_cli,
    "sdk": check_sdk,
    "style": check_style,
}


# --------------------------------------------------------------------------
# Allowlist and entry point.
# --------------------------------------------------------------------------

def load_allowlist(path: Path) -> set[tuple[str, str]]:
    allowed: set[tuple[str, str]] = set()
    if not path.is_file():
        return allowed
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            category, _, value = line.partition(" ")
            allowed.add((category, value.strip()))
    return allowed


def allowed(finding: Finding, allowlist: set[tuple[str, str]]) -> bool:
    return any(
        category == finding.category and fnmatch.fnmatchcase(finding.value, value)
        for category, value in allowlist
    )


def run(docs: Path, root: Path, allowlist: set[tuple[str, str]] | None = None,
        checks: dict | None = None) -> list[Finding]:
    facts = load_facts(root, docs.parent)
    allowlist = allowlist or set()
    findings: list[Finding] = []
    for page_path in sorted(docs.rglob("*.md")):
        rel = page_path.relative_to(docs.parent).as_posix()
        page = segments(page_path.read_text())
        for check in (checks or CHECKS).values():
            findings.extend(f for f in check(page, facts, rel) if not allowed(f, allowlist))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", type=Path, default=DOCS_REPO.parent,
                        help="workspace folder holding the sibling checkouts (default: ..)")
    parser.add_argument("--docs", type=Path, default=DOCS_REPO / "docs")
    parser.add_argument("--allowlist", type=Path,
                        default=DOCS_REPO / "scripts" / "reference-allowlist.txt")
    parser.add_argument("--only", choices=sorted(CHECKS), action="append",
                        help="run only these checks (repeatable)")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    missing = [r for r in REQUIRED if not (root / r).is_dir()]
    if missing:
        print(f"missing sibling checkouts under {root}: {', '.join(missing)}\n"
              "clone them with deploy/scripts/workspace.sh (KIONGA_SRC=<root>)", file=sys.stderr)
        return 2
    absent = [r for r in REPOS if not (root / r).is_dir()]
    if absent:
        print(f"note: not checked out, references into them are skipped: {', '.join(absent)}",
              file=sys.stderr)

    checks = {k: v for k, v in CHECKS.items() if not args.only or k in args.only}
    findings = run(args.docs.resolve(), root, load_allowlist(args.allowlist), checks)
    for finding in findings:
        print(finding)
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.category] = counts.get(finding.category, 0) + 1
    summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "none"
    print(f"\n{len(findings)} unresolved reference(s) [{summary}] "
          f"in {args.docs} against {root}", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
