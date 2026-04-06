from __future__ import annotations

from typing import Any

from streamlit_flow.elements import StreamlitFlowEdge, StreamlitFlowNode
from streamlit_flow.layouts import LayeredLayout, Layout, ManualLayout, TreeLayout
from streamlit_flow.state import StreamlitFlowState

DOMAIN_COLORS = {
    "parties": "#4A90D9",
    "clients": "#50C878",
    "deals": "#E8A838",
    "orders": "#D94A6B",
    "instrument": "#9B59B6",
    "lending": "#1ABC9C",
    "connectivity": "#F39C12",
    "default": "#95A5A6",
}

SV_BG = "#FFFFFF"
SV_BORDER_WIDTH = "3px"
BASE_OPACITY = "1.0"
DIM_OPACITY = "0.85"


def _domain_color(domain: str) -> str:
    return DOMAIN_COLORS.get(domain.lower(), DOMAIN_COLORS["default"])


def _classify_tables(sv: dict[str, Any]) -> tuple[set[str], set[str]]:
    base = set(sv.get("base_tables", []))
    dimension = set()
    for j in sv.get("joins", []):
        t = j.get("table", "")
        if t:
            dimension.add(t)
    dimension -= base
    return base, dimension


def _fmt_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _build_table_node(
    table_name: str,
    table_data: dict[str, Any],
    domain: str,
    role: str,
) -> StreamlitFlowNode:
    col_count = len(table_data.get("columns", []))
    row_count = table_data.get("row_count")
    pk_list = table_data.get("primary_keys", [])
    fk_list = table_data.get("foreign_keys", [])

    subtitle_parts = [f"{col_count} cols"]
    if row_count is not None:
        subtitle_parts.append(f"{_fmt_count(row_count)} rows")
    if pk_list:
        subtitle_parts.append(f"PK: {', '.join(pk_list[:2])}")
    if fk_list:
        subtitle_parts.append(f"FK: {', '.join(fk_list[:2])}")

    content = f"**{table_name}**\n\n{' · '.join(subtitle_parts)}"

    color = _domain_color(domain)

    if role == "base":
        style = {
            "background": color,
            "color": "#FFFFFF",
            "border": f"2px solid {color}",
            "borderRadius": "8px",
            "padding": "10px 14px",
            "fontSize": "11px",
            "fontFamily": "monospace",
            "width": "auto",
            "height": "auto",
        }
    else:
        style = {
            "background": f"{color}CC",
            "color": "#FFFFFF",
            "border": f"2px dashed {color}",
            "borderRadius": "8px",
            "padding": "8px 12px",
            "fontSize": "10px",
            "fontFamily": "monospace",
            "width": "auto",
            "height": "auto",
        }

    return StreamlitFlowNode(
        id=table_name,
        pos=(0, 0),
        data={"content": content},
        node_type="default",
        source_position="bottom",
        target_position="top",
        draggable=True,
        style=style,
    )


def _build_sv_node(
    sv: dict[str, Any],
) -> StreamlitFlowNode:
    sv_name = sv.get("name", "")
    domains = sv.get("domains", [])
    if isinstance(domains, str):
        domains = [domains]
    primary_domain = domains[0] if domains else "default"
    base, dimension = _classify_tables(sv)

    content = (
        f"**{sv_name}**\n\n"
        f"{len(base)} base · {len(dimension)} dim · {len(sv.get('joins', []))} joins"
    )

    color = _domain_color(primary_domain)

    style = {
        "background": SV_BG,
        "color": "#333333",
        "border": f"{SV_BORDER_WIDTH} solid {color}",
        "borderRadius": "12px",
        "padding": "12px 16px",
        "fontSize": "12px",
        "fontWeight": "bold",
        "fontFamily": "monospace",
        "boxShadow": f"0 0 8px {color}44",
        "width": "auto",
        "height": "auto",
    }

    return StreamlitFlowNode(
        id=sv_name,
        pos=(0, 0),
        data={"content": content},
        node_type="input",
        source_position="bottom",
        target_position="top",
        draggable=True,
        style=style,
    )


def build_graph(
    semantic_views: list[dict[str, Any]],
    tables: dict[str, Any],
    mode: str = "all",
    focus_sv: str | None = None,
) -> tuple[StreamlitFlowState, Layout]:
    nodes: list[StreamlitFlowNode] = []
    edges: list[StreamlitFlowEdge] = []
    seen_nodes: set[str] = set()
    edge_id = 0

    def _next_edge_id() -> str:
        nonlocal edge_id
        edge_id += 1
        return f"e{edge_id}"

    if mode == "focus" and focus_sv:
        target_sv = None
        for sv in semantic_views:
            if sv.get("name") == focus_sv:
                target_sv = sv
                break
        if not target_sv:
            return StreamlitFlowState([], []), ManualLayout()

        domains = target_sv.get("domains", [])
        if isinstance(domains, str):
            domains = [domains]
        primary_domain = domains[0] if domains else "default"
        base, dimension = _classify_tables(target_sv)

        sv_name = target_sv.get("name", "")
        nodes.append(_build_sv_node(target_sv))
        seen_nodes.add(sv_name)

        for t in sorted(base):
            if t not in seen_nodes:
                nodes.append(_build_table_node(t, tables.get(t, {}), primary_domain, "base"))
                seen_nodes.add(t)
            edges.append(
                StreamlitFlowEdge(
                    id=_next_edge_id(),
                    source=sv_name,
                    target=t,
                    edge_type="smoothstep",
                    animated=True,
                    marker_end={"type": "arrow"},
                    style={"stroke": _domain_color(primary_domain), "strokeWidth": 2},
                )
            )

        for j in target_sv.get("joins", []):
            left = j.get("join_to", "")
            right = j.get("table", "")
            if not left or not right:
                continue
            if right not in seen_nodes:
                nodes.append(
                    _build_table_node(right, tables.get(right, {}), primary_domain, "dimension")
                )
                seen_nodes.add(right)
            join_type = j.get("join_type", "left")
            edges.append(
                StreamlitFlowEdge(
                    id=_next_edge_id(),
                    source=left,
                    target=right,
                    edge_type="smoothstep",
                    style={"stroke": "#999999", "strokeWidth": 1, "strokeDasharray": "6 3"},
                    label=f"{join_type.upper()}",
                    label_style={"fontSize": "10px", "fill": "#FFFFFF", "fontWeight": "bold"},
                    label_show_bg=True,
                    label_bg_style={"fill": "#555555", "fillOpacity": 0.9},
                    marker_end={"type": "arrowclosed"},
                )
            )

        layout = TreeLayout(direction="down", node_node_spacing=100)

    else:
        for sv in semantic_views:
            sv_name = sv.get("name", "")
            domains = sv.get("domains", [])
            if isinstance(domains, str):
                domains = [domains]
            primary_domain = domains[0] if domains else "default"
            base, dimension = _classify_tables(sv)

            if sv_name not in seen_nodes:
                nodes.append(_build_sv_node(sv))
                seen_nodes.add(sv_name)

            for t in sorted(base):
                if t not in seen_nodes:
                    nodes.append(_build_table_node(t, tables.get(t, {}), primary_domain, "base"))
                    seen_nodes.add(t)
                edges.append(
                    StreamlitFlowEdge(
                        id=_next_edge_id(),
                        source=sv_name,
                        target=t,
                        edge_type="smoothstep",
                        animated=True,
                        marker_end={"type": "arrow"},
                        style={"stroke": _domain_color(primary_domain), "strokeWidth": 2},
                    )
                )

            for j in sv.get("joins", []):
                left = j.get("join_to", "")
                right = j.get("table", "")
                if not left or not right:
                    continue
                if right not in seen_nodes:
                    nodes.append(
                        _build_table_node(right, tables.get(right, {}), primary_domain, "dimension")
                    )
                    seen_nodes.add(right)
                join_type = j.get("join_type", "left")
                edges.append(
                    StreamlitFlowEdge(
                        id=_next_edge_id(),
                        source=left,
                        target=right,
                        edge_type="smoothstep",
                        style={"stroke": "#999999", "strokeWidth": 1, "strokeDasharray": "6 3"},
                        label=f"{join_type.upper()}",
                        label_style={"fontSize": "10px", "fill": "#FFFFFF", "fontWeight": "bold"},
                        label_show_bg=True,
                        label_bg_style={"fill": "#555555", "fillOpacity": 0.9},
                        marker_end={"type": "arrowclosed"},
                    )
                )

        layout = LayeredLayout(direction="down", node_node_spacing=200, node_layer_spacing=250)

    state = StreamlitFlowState(nodes, edges)
    return state, layout
