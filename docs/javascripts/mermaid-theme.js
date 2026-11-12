/* Kionga theme for Mermaid diagrams.
 *
 * Material for MkDocs renders each diagram into a closed shadow root and calls
 * mermaid.initialize() once, passing its own themeCSS. Page stylesheets cannot
 * reach inside that shadow root, so the Kionga styling is appended to Material's
 * themeCSS here. Colors are CSS custom properties defined in
 * stylesheets/diagrams.css; they inherit into the shadow root, so light and dark
 * schemes both work without touching diagram sources.
 *
 * Diagram sources only tag nodes with one of four roles:
 *   class <ids> core | data | runtime | external
 * This file must stay identical in docs and engineering-docs. */
(function () {
  if (typeof mermaid === "undefined" || mermaid.__kionga) return;

  var role = function (name, dashed) {
    var shape = ".node." + name + " :is(rect,polygon,path,circle,ellipse)";
    return (
      shape + "{fill:var(--kd-" + name + "-bg)!important;stroke:var(--kd-" + name + "-line)!important;" +
      (dashed ? "stroke-dasharray:4 3;" : "") + "}" +
      ".node." + name + " :is(.nodeLabel,.nodeLabel p,span,text){color:var(--kd-" + name + "-ink)!important;fill:var(--kd-" + name + "-ink)!important}"
    );
  };

  var css = [
    /* default nodes */
    ".node :is(rect,polygon,path,circle,ellipse){stroke-width:1px}",
    ".node rect{rx:6px;ry:6px}",
    ".nodeLabel,.nodeLabel p{line-height:1.4}",
    /* groups read as quiet bands with a small caps label */
    ".cluster rect{fill:var(--kd-cluster-bg)!important;stroke:var(--kd-node-line)!important;stroke-width:1px!important;rx:10px;ry:10px}",
    ".cluster-label :is(.nodeLabel,span,p){font-family:'Familjen Grotesk',system-ui,sans-serif;font-weight:600;font-size:13px;letter-spacing:.04em;text-transform:uppercase;color:var(--kd-muted,var(--kd-ext-ink))!important}",
    /* edges */
    ".flowchart-link{stroke-width:1.25px!important}",
    ".edgeLabel,.edgeLabel p,.edgeLabel span{font-size:12px;color:var(--kd-ext-ink)!important}",
    /* semantic roles */
    role("core"), role("data"), role("run"), role("ext", true),
    /* sequence diagrams */
    ".actor{stroke-width:1px!important}",
    "text.actor>tspan{font-weight:600}",
    ".note{stroke-width:1px!important}",
    ".labelBox{stroke-width:1px!important}",
  ].join("");

  /* role names in diagram sources -> token prefixes in diagrams.css */
  css = css
    .replace(/\.node\.run\b/g, ".node.runtime")
    .replace(/\.node\.ext\b/g, ".node.external");

  var initialize = mermaid.initialize.bind(mermaid);
  mermaid.initialize = function (config) {
    config = config || {};
    initialize(Object.assign({}, config, {
      themeCSS: (config.themeCSS || "") + css,
      flowchart: Object.assign({ nodeSpacing: 36, rankSpacing: 52, padding: 12, curve: "basis", wrappingWidth: 220 }, config.flowchart),
      sequence: Object.assign({ mirrorActors: false, wrap: true, width: 168, actorMargin: 44, boxMargin: 10, noteMargin: 12, messageMargin: 32 }, config.sequence),
    }));
  };
  mermaid.__kionga = true;
})();
