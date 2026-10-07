"""Final Research Map packaging of the validated, semantically distinct projections.

The older renderers are pure intermediate representations and bounded migration
readers. Only this package is written by the supported workspace harness.
"""

import json
import posixpath
import re
from dataclasses import dataclass
from functools import cache
from pathlib import PurePosixPath
from urllib.parse import quote, unquote, urlsplit

from . import knowledge_graph as graph
from . import obsidian_semantics as semantics
from . import private_projection as public
from . import private_views as views
from .preferred_paths import FAMILIES, HOME, INTERNAL, PRODUCT, preferred_paths
from .private_projection import ProjectionError, markdown_parts, read_yaml, utf8, yaml_text
from .validator import Atlas

MODES = {
    "architecture": "Architecture",
    "knowledge-detail": "Knowledge Detail",
    "rq-overlay": "Questions",
}
MANIFESTS = {
    public.OWNER: INTERNAL / "Manifests/technical-atlas.yaml",
    views.OWNER: INTERNAL / "Manifests/research-map.yaml",
}
LEDGER = INTERNAL / "Migration/routes.yaml"


@dataclass(frozen=True)
class ProductTree:
    files: dict[PurePosixPath, bytes]
    owners: dict[PurePosixPath, str]
    routes: dict[PurePosixPath, PurePosixPath]


def package(atlas: Atlas, technical: dict, derived: dict) -> ProductTree:
    """Inventory every old path before rendering; preserve all mode audit sections."""
    preferred = preferred_paths(atlas)
    old_pages = views.identity_page_paths(atlas)
    old = {public.OWNED_ROOT / p: data for p, data in technical.items()}
    old.update({views.OWNED_ROOT / p: data for p, data in derived.items()})
    routes: dict[PurePosixPath, PurePosixPath] = {}
    retained: dict[PurePosixPath, PurePosixPath] = {}

    def route(source: PurePosixPath, target: PurePosixPath, *, keep: bool = True) -> None:
        routes[source] = target
        if keep:
            if target in retained.values():
                raise ProjectionError("Duplicate preferred destination")
            retained[source] = target

    public_fixed = {
        public.INDEX: INTERNAL / "Indexes/atlas-id-index.yaml",
        public.ANATOMY: PRODUCT / "Diagrams/Agent Anatomy.excalidraw.md",
        public.DOMAIN_SLICE: PRODUCT / "Diagrams/Evidence, Memory & Retrieval.excalidraw.md",
        public.HERO_ASSET: INTERNAL / "Assets/Agent Anatomy Hero.svg",
        public.MANIFEST: MANIFESTS[public.OWNER],
    }
    for path in technical:
        source = public.OWNED_ROOT / path
        if path in {public.HOME, public.MAP}:
            route(source, HOME if path == public.HOME else public_fixed[public.ANATOMY], keep=False)
        elif path in public_fixed:
            route(source, public_fixed[path])
        else:
            node = atlas.entities[path.stem]
            route(
                source,
                INTERNAL
                / "Registry"
                / ("Evidence" if node.type == "Evidence" else "Records")
                / path.name,
            )
    fixed = {
        views.MANIFEST: MANIFESTS[views.OWNER],
        views.K3_HOME: HOME,
        views.REFERENCE_INDEX: INTERNAL / "Indexes/declared-reference-index.yaml",
        views.SOURCE_INDEX: INTERNAL / "Indexes/source-resolution-index.yaml",
        views.NAVIGATION: INTERNAL / "Audit/Declared References.md",
        views.SOURCE_DETAIL: INTERNAL / "Audit/Source Details.md",
        views.RESEARCH_LANDSCAPE: PRODUCT / "Views/Research Steering.md",
        views.LITERATURE_INSPECTION: PRODUCT / "Views/Literature Inspection.md",
    }
    page_ids = {path: identity for identity, path in old_pages.items()}
    hub_aux = {
        path: identity
        for identity, hub in views.COMPONENT_HUB_PATHS.items()
        for path in (hub.technical, hub.research)
    }
    for path in derived:
        source = views.OWNED_ROOT / path
        if path in fixed:
            route(source, fixed[path])
        elif path in page_ids:
            route(source, preferred[page_ids[path]])
        elif path in hub_aux:
            route(source, preferred[hub_aux[path]], keep=False)
        elif path.parent == views.HIERARCHY_DIR:
            route(
                source,
                preferred.get(
                    path.stem,
                    routes[public.OWNED_ROOT / public.private_path(atlas.entities[path.stem])],
                ),
                keep=False,
            )
        elif path in {views.INDEX, views.HIERARCHY}:
            route(source, HOME, keep=False)
        elif path == views.OBSERVE_SCOPE:
            route(source, preferred["FUNC-OBSERVE"], keep=False)
        elif path.parent == views.TECHNICAL_DETAIL_ROOT:
            route(
                source,
                PRODUCT / "Diagrams/Technical Relations" / path.name
                if path.suffix == ".canvas"
                else preferred[path.stem],
                keep=path.suffix == ".canvas",
            )
        elif path.parent == views.RQ_ROOT:
            route(source, PRODUCT / "Research/Question Readers" / path.name)
        elif path.suffix == ".base":
            route(source, PRODUCT / "Tables" / path.name)
        elif path.is_relative_to(graph.SCOPES):
            component, mode, *rest = path.relative_to(graph.SCOPES).parts
            if rest == ["Graph Profile.md"]:
                route(source, PRODUCT / "Graphs" / (component + ".md"), keep=False)
            elif rest == ["Edge Audit.md"]:
                route(source, INTERNAL / "Graphs" / component / "Edge Audit.md", keep=False)
            else:
                folder = "Question Overlay" if rest[0] == "optional-rq-overlay" else "Nodes"
                route(source, INTERNAL / "Graphs" / component / MODES[mode] / folder / rest[1])
        elif path.is_relative_to(graph.ROOT):
            target = (
                INTERNAL / "Graphs" / graph.MEMORY / "Edge Audit.md"
                if path.name == "Edge Audit.md"
                else PRODUCT / "Graphs" / (graph.MEMORY + ".md")
            )
            route(source, target, keep=False)
        else:
            raise ProjectionError(f"Unclassified generated path: {path}")

    # Finite supported pre-human-filename Hub aliases, never wildcard ownership.
    for source, identity in (
        (views.LEGACY_MEMORY_WORKBENCH, "CMP-MEM-RETRIEVAL"),
        (views.LEGACY_VERIFIER_WORKBENCH, "CMP-INDEPENDENT-VERIFIER"),
    ):
        routes[views.OWNED_ROOT / source] = preferred[identity]

    # Extensionless WikiLinks, explicit suffix routes, and folder Graph/Base filters.
    replacements = {str(s): str(t) for s, t in routes.items()}
    replacements.update(
        {
            str(s.with_suffix("")): str(t.with_suffix(""))
            for s, t in routes.items()
            if s.suffix == ".md"
        }
    )
    replacements[str(public.OWNED_ROOT / "records")] = str(INTERNAL / "Registry/Records")
    replacements[str(public.OWNED_ROOT / "evidence")] = str(INTERNAL / "Registry/Evidence")
    for identity in preferred:
        if atlas.entities[identity].type != "Component":
            continue
        for mode, title in MODES.items():
            old_root = views.OWNED_ROOT / graph.scope_root(identity, mode)
            new_root = INTERNAL / "Graphs" / identity / title
            replacements[str(old_root / "nodes")] = str(new_root / "Nodes")
            replacements[str(old_root / "optional-rq-overlay")] = str(new_root / "Question Overlay")
    pattern = re.compile(
        "|".join(re.escape(s) for s in sorted(replacements, key=lambda s: (-len(s), s)))
    )

    hub_aux_paths = {views.OWNED_ROOT / path for path in hub_aux}
    hub_overviews = {
        views.OWNED_ROOT / paths.overview for paths in views.COMPONENT_HUB_PATHS.values()
    }
    raw_identities = {
        routes[public.OWNED_ROOT / public.private_path(node)].with_suffix(""): identity
        for identity, node in atlas.entities.items()
    }

    # Reuse pure link normalization only within this exact product build.
    @cache
    def navigation(link: str) -> str:
        value, separator, label = link[2:-2].partition("|")
        escaped_separator = value.endswith("\\")
        if escaped_separator:
            value = value[:-1]
        path, fragment, anchor = value.partition("#")
        old_path = PurePosixPath(path)
        if old_path not in routes:
            old_path = PurePosixPath(path + ".md")
        target = routes.get(old_path)
        if target is None:
            return link
        if old_path.is_relative_to(views.OWNED_ROOT / graph.SCOPES):
            _, mode, *rest = old_path.relative_to(views.OWNED_ROOT / graph.SCOPES).parts
            if rest in (["Graph Profile.md"], ["Edge Audit.md"]):
                anchor = MODES[mode]
                fragment = "#"
                if label in graph.MODES:
                    label = MODES[label]
                if rest == ["Edge Audit.md"] and label == "Edge Audit / detail":
                    label = anchor + " Edge Audit"
        elif old_path.is_relative_to(views.OWNED_ROOT / graph.ROOT):
            fragment, anchor = "#", MODES["architecture"]
            label = (
                "Architecture Edge Audit"
                if old_path.name == "Edge Audit.md"
                else "Architecture Graph guide"
            )
        if target == HOME:
            label = "Home"
            fragment = anchor = ""
        elif old_path == views.OWNED_ROOT / views.RESEARCH_LANDSCAPE:
            label = "Research Steering"
        elif old_path in hub_overviews and label in {
            "Hub Overview",
            "Open Overview",
            "Back to Hub Overview",
        }:
            name = atlas.entities[page_ids[old_path.relative_to(views.OWNED_ROOT)]].name
            label = ("Back to " if label.startswith("Back to ") else "") + name
        elif old_path in hub_aux_paths:
            label = "Consolidated detail audit"
            fragment, anchor = "#", "Consolidated detail audit"
        elif old_path.parent == views.OWNED_ROOT / views.TECHNICAL_DETAIL_ROOT:
            if old_path.suffix == ".md":
                label = "Open " + atlas.entities[old_path.stem].name
        route_text = str(
            target.with_suffix("")
            if old_path.suffix == ".md" and not path.endswith(".md")
            else target
        )
        delimiter = "\\|" if escaped_separator else "|"
        return (
            "[[" + route_text + fragment + anchor + (delimiter + label if separator else "") + "]]"
        )

    def rewrite(data: bytes, source: PurePosixPath, destination: PurePosixPath) -> bytes:
        text = utf8(data)
        if (
            source.is_relative_to(views.OWNED_ROOT)
            and source.relative_to(views.OWNED_ROOT) in page_ids
        ):
            # Retire primary pilot shortcuts before normalizing their old aliases.
            text = re.sub(r"(?m)^.*Historical Memory pilot (?:profile|audit).*$", "", text)

        # Navigation aliases/sections are rewritten separately from machine paths.
        text = re.sub(r"\[\[([^\]]+)\]\]", lambda match: navigation(match[0]), text)

        # Relative authored routes are rebased, never rewritten at their masters.
        def markdown(match: re.Match) -> str:
            value = match[1]
            parsed = urlsplit(value)
            if parsed.scheme or parsed.netloc or value.startswith(("/", "#")):
                return match[0]
            absolute = PurePosixPath(posixpath.normpath(str(source.parent / unquote(parsed.path))))
            target = routes.get(absolute, absolute)
            relative = posixpath.relpath(str(target), str(destination.parent))
            suffix = ("?" + parsed.query if parsed.query else "") + (
                "#" + parsed.fragment if parsed.fragment else ""
            )
            return "](" + quote(relative, safe="/.-_") + suffix + ")"

        text = re.sub(r"\]\(([^)\s]+)\)", markdown, text)
        text = pattern.sub(lambda m: replacements[m[0]], text)
        text = text.replace(
            "- [[Research Map Home|Home]]\n- [[Research Map Home|Home]]",
            "- [[Research Map Home|Home]]",
        )
        if destination.suffix == ".base":
            text = text.replace(
                'file.inFolder("_generated/technical-atlas")',
                'file.inFolder("_Research Map Internals/Registry")',
            )
            text = text.replace(
                "'!file.inFolder(\"_generated\")'",
                "'!file.inFolder(\"_generated\")'\n"
                "    - '!file.inFolder(\"Research Map\")'\n"
                "    - '!file.inFolder(\"_Research Map Internals\")'",
            )
        # Machine metadata must describe the final destination, too.
        for key in ("identity_page_path", "rq_page_path", "graph_path"):
            text = re.sub(r"(?m)^" + key + r": .*?$", key + ": " + str(destination), text)
        if destination.suffix == ".canvas":
            canvas = json.loads(text)

            def card_link(match: re.Match) -> str:
                identity = raw_identities.get(PurePosixPath(match[1]))
                if identity is None:
                    return match[0]
                node = atlas.entities[identity]
                if identity not in preferred:
                    return f"[[{match[1]}|Evidence audit / provenance]]"
                return (
                    f"[[{preferred[identity].with_suffix('')}|{node.name}]]\n\n"
                    "> [!info]- Registry audit\n"
                    f"> [[{match[1]}|Raw Registry record]]"
                )

            for card in canvas["nodes"]:
                if card["type"] == "text":
                    card["text"] = re.sub(r"\[\[([^|]+)\|[^\]]+\]\]", card_link, card["text"])
            text = json.dumps(canvas, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        return text.encode()

    files = {}
    owners = {}
    for source, destination in retained.items():
        if destination in MANIFESTS.values():
            continue
        files[destination] = rewrite(old[source], source, destination)
        owners[destination] = (
            public.OWNER if source.is_relative_to(public.OWNED_ROOT) else views.OWNER
        )

    steering = PRODUCT / "Views/Research Steering.md"
    files[steering] = re.sub(
        r"(?ms)^## Graph navigation\n.*?(?=^## )",
        "## Graph navigation\n\n"
        "[[Research Map/Views/Graphs|Graphs — choose a Component and mode]]\n\n",
        utf8(files[steering]),
    ).encode()

    def add(path: PurePosixPath, body: str, owner: str = views.OWNER) -> None:
        if path in files:
            raise ProjectionError("Duplicate final product path")
        files[path] = (
            "---\n"
            + yaml_text(dict(generated_by=owner, privacy="private", export_policy="deny"))
            + "---\n"
            + body
            + "\n"
        ).encode()
        owners[path] = owner

    for identity, page in preferred.items():
        node = atlas.entities[identity]
        if identity not in old_pages:
            raw = public.OWNED_ROOT / public.private_path(node)
            add(
                page,
                f"# {node.name}\n\nType: {node.type}\n\n"
                f"[[{HOME.with_suffix('')}|Home]]\n\n"
                "[Technical](#technical) · [Research](#research) · [Sources](#sources)\n\n"
                f"## Technical\n\n{node.description}\n\n## Research\n\n"
                "Public Registry/program context only; "
                "no private scientific authority inferred.\n\n"
                "## Sources\n\n> [!info]- Complete Registry audit\n"
                + "\n".join("> " + line for line in utf8(files[routes[raw]]).splitlines())
                + f"\n\n[[{HOME.with_suffix('')}|Return Home]]",
            )
        else:
            # Preserve unique retired detail/hub content within the preferred audit.
            companions = [
                views.OWNED_ROOT / p for p, subject in hub_aux.items() if subject == identity
            ]
            detail = views.TECHNICAL_DETAIL_ROOT / (identity + ".md")
            if detail in derived:
                companions.append(views.OWNED_ROOT / detail)
            extras = []
            for companion in companions:
                body = markdown_parts(utf8(rewrite(old[companion], companion, page)))[1]
                body = body.replace("*Component Hub ·", "*Component detail ·")
                body = body.replace("Originating Component Hub(s)", "Originating Components")
                extras += [
                    "> [!info]- Complete consolidated detail audit",
                    ">",
                    *("> " + line for line in body.splitlines()),
                    "",
                ]
            text = utf8(files[page])
            text = text.replace(
                "\n\n---\n",
                f"\n\n[[{HOME.with_suffix('')}|Home]] · [[#Technical|Technical]] · "
                "[[#Research|Research]] · [[#Sources & verification|Sources]]\n\n---\n",
                1,
            )
            files[page] = (
                text
                + ("\n## Consolidated detail audit\n\n" + "\n".join(extras) if extras else "")
                + f"\n[[{HOME.with_suffix('')}|Return Home]]\n"
            ).encode()

    for identity, node in sorted(atlas.entities.items()):
        if node.type != "Component":
            continue
        guide = PRODUCT / "Graphs" / (identity + ".md")
        audit = INTERNAL / "Graphs" / identity / "Edge Audit.md"
        guide_sections = [
            f"# Graphs — {node.name}",
            f"[[{HOME.with_suffix('')}|Home]] · "
            f"[[{preferred[identity].with_suffix('')}|{node.name}]]",
            " · ".join(f"[[#{title}|{title}]]" for title in MODES.values()),
        ]
        audit_sections = [
            f"# Edge Audit — {node.name}",
            "Effective identity: (Component, mode, directed pair). Modes never union.",
            " · ".join(f"[[#{title}|{title}]]" for title in MODES.values()),
        ]
        bodies: dict[str, dict[str, str]] = {}
        for mode, title in MODES.items():
            root = views.OWNED_ROOT / graph.scope_root(identity, mode)
            bodies[mode] = {}
            for name in ("Graph Profile.md", "Edge Audit.md"):
                source = root / name
                body = markdown_parts(
                    utf8(
                        rewrite(old[source], source, guide if name == "Graph Profile.md" else audit)
                    )
                )[1]
                body = re.sub(r"(?m)^# Knowledge Graph .*\n?", "", body, count=1)
                body = body.replace("Domain/Function/Assembly", "Domain/Function")
                body = body.replace(
                    "Open Edge Audit.md in this folder for the complete Markdown fallback, "
                    "inventory and inspection routes.",
                    f"[[{audit.with_suffix('')}#{title}|{title} Edge Audit]] provides the "
                    "complete Markdown fallback, inventory and inspection routes.",
                )
                body = body.replace(
                    "Classes/exclusions and manual activation are in Graph Profile.md; "
                    "only the two node folders enter the filters.",
                    f"Classes/exclusions and manual activation are in "
                    f"[[{guide.with_suffix('')}#{title}|the {title} guide section]]; "
                    "only the two node folders enter the filters.",
                )
                bodies[mode][name] = body
        # Factor only identical prose, never filters, tables, diagnostics or mode rows.
        first_blocks = bodies["architecture"]["Graph Profile.md"].split("\n\n")
        common = list(
            dict.fromkeys(
                block
                for block in first_blocks
                if block.strip()
                and not block.startswith(("#", "```", "- ", "| "))
                and not block.rstrip().endswith(":")
                and "[[" not in block
                and all(block in bodies[mode]["Graph Profile.md"].split("\n\n") for mode in MODES)
            )
        )
        guide_sections += ["## Shared instructions", *common]
        for mode, title in MODES.items():
            profile = "\n\n".join(
                block
                for block in bodies[mode]["Graph Profile.md"].split("\n\n")
                if block not in common
            )
            guide_sections += [f"\n## {title}\n", re.sub(r"(?m)^(#+) ", r"##\1 ", profile)]
            audit_sections += [
                f"\n## {title}\n",
                re.sub(r"(?m)^(#+) ", r"##\1 ", bodies[mode]["Edge Audit.md"]),
            ]
        add(guide, "\n\n".join(guide_sections))
        add(audit, "\n\n".join(audit_sections))
    add(
        PRODUCT / "Views/Graphs.md",
        "# Graphs\n\n[[Research Map Home|Home]]\n\n"
        + "\n".join(
            f"- [[{PRODUCT / 'Graphs' / identity}|{atlas.entities[identity].name}]]"
            for identity in preferred
            if atlas.entities[identity].type == "Component"
        ),
    )
    add(
        PRODUCT / "Guides/Using the Research Map.md",
        "# Using the Research Map\n\n[[Research Map Home|Home]]\n\n"
        "Navigate System → Component using only Registry part_of. Functions describe context.\n\n"
        "Technical / Research / Sources sections share one preferred page. "
        "Audits are collapsed.\n\n"
        "Graph modes Architecture, Knowledge Detail and Questions are separate projections.\n\n"
        "Private RQ Readers are reading projections; edit the authored master. All other private "
        "scientific records retain their exact authored routes.\n\n"
        "Generated pages are disposable; Git Registry and authored Research remain their "
        "respective authorities.\n\n"
        "Internal storage has no landing page. Agent Anatomy and Evidence, Memory & Retrieval "
        "are secondary diagrams.",
    )
    home = [
        "# Research Map Home",
        "",
        "Start with the System, then follow Component children. Only Registry part_of creates "
        "technical depth. Functions provide functional context.",
        "",
        "Current state: generated navigation from the checked source revision. "
        "Missing Research mappings imply no novelty, gap or completeness judgment.",
        "",
    ]
    system_paths = [p for i, p in preferred.items() if atlas.entities[i].type == "System"]
    home += ["## Start here", ""]
    home += [
        f"- Explore technical composition: [[{p.with_suffix('')}|System]]" for p in system_paths
    ]
    home += [
        "- Explore functional context: [[#Functions|Functions]]",
        "- Read scientific inventories: [[Research Map/Views/Research Steering|Research Steering]]",
        "- Inspect literature: [[Research Map/Views/Literature Inspection|Literature Inspection]]",
        "- Inspect a Component Graph: [[Research Map/Views/Graphs|Graphs]]",
        "- Learn navigation: [[Research Map/Guides/Using the Research Map|Using the Research Map]]",
        "",
        "## Secondary explanatory diagrams",
        "",
    ]
    home += [
        f"- [[{path.with_suffix('')}|{path.stem.removesuffix('.excalidraw')}]]"
        for path in (
            PRODUCT / "Diagrams/Agent Anatomy.excalidraw.md",
            PRODUCT / "Diagrams/Evidence, Memory & Retrieval.excalidraw.md",
        )
    ]
    home += [
        "",
        "Markdown fallback: preferred pages and mode-specific Edge Audits remain "
        "readable if Excalidraw, Canvas, native Graph or Bases are unavailable.",
        "",
        "Private Research stays at its authored locations. Private RQ reading projections "
        "are under Research Map/Research/Question Readers; all other scientific masters "
        "are linked at their existing authored paths.",
        "",
        "## Tables",
        "",
    ]
    home += [f"- [[{path}|{path.stem}]]" for path in sorted(files) if path.suffix == ".base"]
    labels = {
        "System": "System",
        "Component": "Components",
        "Function": "Functions",
        "Interface": "Interfaces",
        "Contract": "Contracts",
        "DataArtifact": "Data Artifacts",
        "MeasurementPoint": "Measurements",
        "Environment": "Environments",
        "ResearchQuestion": "Program Research Questions",
        "ResearchThread": "Program Research Threads",
        "Decision": "Project Decisions",
    }
    home += [
        "",
        "## Complete identity inventory",
        "",
        "Flat inventories below are not a hierarchy or a runtime sequence.",
        "",
    ]
    for kind in FAMILIES:
        home += [f"> [!info]- {labels[kind]}", ">", f"> ## {labels[kind]}", ">"]
        home += [
            f"> - [[{path.with_suffix('')}|{atlas.entities[i].name}]]"
            for i, path in preferred.items()
            if atlas.entities[i].type == kind
        ]
        home.append("")
    properties = markdown_parts(utf8(files[HOME]))[0]
    files[HOME] = ("---\n" + yaml_text(properties) + "---\n" + "\n".join(home) + "\n").encode()

    # Atlas index paths are vault-relative final routes, never old-root-relative paths.
    index = INTERNAL / "Indexes/atlas-id-index.yaml"
    entries = read_yaml(utf8(files[index]))
    for identity, item in entries["entries"].items():
        item["path"] = str(
            routes[public.OWNED_ROOT / public.private_path(atlas.entities[identity])]
        )
        if identity in preferred:
            item["preferred_path"] = str(preferred[identity])
    files[index] = yaml_text(entries).encode()
    files[LEDGER] = yaml_text(
        dict(
            migration_schema_version="1.0",
            generated_by=views.OWNER,
            routes={str(s): str(t) for s, t in sorted(routes.items())},
        )
    ).encode()
    owners[LEDGER] = views.OWNER
    for owner, manifest_path in MANIFESTS.items():
        old_manifest = (
            technical[public.MANIFEST] if owner == public.OWNER else derived[views.MANIFEST]
        )
        provenance = read_yaml(utf8(old_manifest))
        provenance.pop("owned_files")
        inventory = []
        for path, data in sorted(files.items()):
            if owners[path] != owner:
                continue
            row = dict(path=str(path), **semantics.record(data, path, owner))
            inventory.append(row)
        files[manifest_path] = yaml_text(
            dict(
                product_schema_version="1.1",
                generated_by=owner,
                provenance=provenance,
                owned_files=inventory,
            )
        ).encode()
        owners[manifest_path] = owner
    public.validate_portable_paths(files)
    return ProductTree(files, owners, routes)
