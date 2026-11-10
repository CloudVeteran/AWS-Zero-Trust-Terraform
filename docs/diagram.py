"""Draw the lab architecture as docs/architecture.png.

The picture is only what Terraform creates. It does not show an internet
gateway, a route through the firewall, a Verified Access endpoint, IAM
Identity Center, or PrivateLink, and it does not show a person reaching an app.

Regenerate from the repository root, with Graphviz installed:

    pip install diagrams
    python docs/diagram.py
"""

import struct
from pathlib import Path

from graphviz import Digraph
from diagrams import Cluster, Diagram, Edge, Node
from diagrams.aws.network import NetworkFirewall, PrivateSubnet, VPC
from diagrams.aws.security import Guardduty, SecurityHub
from diagrams.generic.device import Tablet

try:
    from diagrams.aws.network import VerifiedAccess
except ImportError:
    # diagrams 0.25.1 on PyPI has no Verified Access class yet. The PNG next
    # to this file is the official AWS architecture icon from the diagrams
    # repo, so `pip install diagrams` still regenerates the picture.
    class VerifiedAccess(Node):
        _provider = "aws"
        _type = "network"
        _icon_dir = str(Path(__file__).resolve().parent / "icons")
        _icon = "verified-access.png"


FONT = "DejaVu Sans"
OUT = Path(__file__).resolve().parent / "architecture"
TARGET_WIDTH = 1600


def rank_row(parent, *nodes):
    """Keep nodes on one horizontal row, left to right, in a top-to-bottom graph."""
    group = Digraph()
    group.attr(rank="same")
    for node in nodes:
        group.node(node.nodeid)
    for left, right in zip(nodes, nodes[1:]):
        group.edge(left.nodeid, right.nodeid, style="invis")
    parent.dot.subgraph(group)


def styled(**extra):
    attrs = dict(
        fontname=FONT,
        fontsize="15",
        fontcolor="#16191F",
        penwidth="1.8",
        color="#31414F",
    )
    attrs.update(extra)
    return Edge(**attrs)


def frame(fill, border, size="17", margin="0.26", pen="2.2"):
    return dict(
        fontname=FONT,
        fontcolor="#16191F",
        style="rounded,filled",
        margin=margin,
        labeljust="l",
        fillcolor=fill,
        color=border,
        penwidth=pen,
        fontsize=size,
    )


def icon(cls, label, **attrs):
    """Leave enough room under the icon that the label is not drawn on top of it."""
    lines = label.count("\n") + 1
    attrs.setdefault("height", {1: "3.05", 2: "3.25", 3: "3.75"}[lines])
    attrs.setdefault("imagepos", "tc")
    return cls(label, **attrs)


def png_size(path):
    with open(path, "rb") as handle:
        header = handle.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"{path} is not a PNG")
    return struct.unpack(">II", header[16:24])


def draw(dpi):
    graph_attr = {
        "bgcolor": "white",
        "pad": "0.3",
        "nodesep": "0.5",
        "ranksep": "0.5",
        "fontname": FONT,
        "fontsize": "28",
        "fontcolor": "#16191F",
        "labelloc": "t",
        "dpi": str(dpi),
        "splines": "spline",
    }
    node_attr = {
        "fontname": FONT,
        "fontsize": "16",
        "fontcolor": "#16191F",
        "fixedsize": "false",
        "imagepos": "tc",
        "labelloc": "b",
    }
    edge_attr = {
        "fontname": FONT,
        "fontsize": "15",
        "fontcolor": "#16191F",
    }

    with Diagram(
        "AWS Zero Trust lab\nWhat this code creates",
        filename=str(OUT),
        show=False,
        direction="TB",
        outformat="png",
        graph_attr=graph_attr,
        node_attr=node_attr,
        edge_attr=edge_attr,
    ):
        with Cluster(
            "One AWS account, one Region",
            graph_attr=frame("#F7F8FA", "#232F3E", "18", "0.32", "2.4"),
        ):
            with Cluster(
                "Watches the account",
                graph_attr=frame("#F3E8FB", "#6B3FA0", "16", "0.26", "2"),
            ) as monitoring:
                guardduty = icon(Guardduty, "Threat detection\n(GuardDuty)")
                securityhub = icon(
                    SecurityHub,
                    "Compliance checks:\nNIST 800-53 Rev. 5\n(Security Hub)",
                )
                guardduty >> styled(
                    label="sends findings",
                    color="#C45500",
                    fontcolor="#8A3B00",
                    penwidth="2.4",
                    constraint="false",
                ) >> securityhub
                rank_row(monitoring, guardduty, securityhub)

            with Cluster(
                "Device check only. No app behind it",
                graph_attr=frame("#FFF6E4", "#C47B00", "16", "0.26", "2"),
            ) as trust:
                verified = icon(VerifiedAccess, "Verified Access\n(no app endpoint)")
                jamf = icon(Tablet, "Device trust check\n(Jamf)")
                verified - styled(label="attached", constraint="false") - jamf
                rank_row(trust, verified, jamf)

            with Cluster(
                "Private network (VPC)   10.0.0.0/16\nNo internet gateway",
                graph_attr=frame("#E8F7EB", "#1B7A32", "17", "0.3", "2.2"),
            ) as vpc_box:
                # fixedsize keeps the short label under the icon instead of on it.
                vpc = icon(
                    VPC,
                    "VPC",
                    fixedsize="true",
                    width="2.35",
                    height="3.05",
                    imagescale="true",
                )
                subnet1 = icon(
                    PrivateSubnet,
                    "Private subnet 1\n10.0.16.0/20, zone 1",
                    group="subnet1",
                )
                subnet2 = icon(PrivateSubnet, "Private subnet 2\n10.0.32.0/20, zone 2")
                subnet3 = icon(PrivateSubnet, "Private subnet 3\n10.0.48.0/20, zone 3")
                firewall = icon(
                    NetworkFirewall,
                    "Network Firewall\n(no rules yet)",
                    group="subnet1",
                )
                vpc - styled(constraint="false") - subnet1
                subnet1 - styled(constraint="false") - subnet2
                subnet2 - styled(constraint="false") - subnet3
                subnet1 - styled(
                    label="endpoint lives here\nno traffic routed",
                    style="dashed",
                    color="#545B64",
                    constraint="true",
                    tailport="s",
                    headport="n",
                    weight="8",
                ) - firewall
                rank_row(vpc_box, vpc, subnet1, subnet2, subnet3)

            # Invisible edges only stack the three groups. They are not
            # connections in AWS. GuardDuty, the VPC, and Verified Access
            # are separate, and nothing here joins them.
            securityhub >> styled(style="invis", constraint="true") >> vpc
            verified >> styled(style="invis", constraint="true") >> vpc
            jamf >> styled(style="invis", constraint="true") >> vpc


def main():
    draw(100)
    width, _height = png_size(OUT.with_suffix(".png"))
    draw(round(100 * TARGET_WIDTH / width))


if __name__ == "__main__":
    main()
