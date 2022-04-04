import os
import html
import ibis.models
import random
import networkx as nx
import drawSvg as draw

from django.conf import settings
from fa2 import ForceAtlas2
from collections import defaultdict
from api.utils import get_submodel

HEIGHT, WIDTH, PADDING = 1080, 1080, 50  # dimensions of SVG image
MIN_SIZE, MAX_SIZE = 1, 10
MIN_OPACITY, MAX_OPACITY = 0, 0.75


def graph():
    G = nx.Graph()

    edges = defaultdict(lambda: 0)
    for donation in ibis.models.Donation.objects.all():
        edges[(donation.user.id, donation.target.id)] += donation.amount

    for edge, weight in edges.items():
        G.add_edge(*edge, weight=weight)

    nx.set_node_attributes(
        G,
        {
            y: {
                'label':
                str(ibis.models.User.objects.get(id=y)),
                'type':
                get_submodel(
                    ibis.models.User.objects.get(id=y)).__name__.lower(),
            }
            for y in set(x for edge in edges for x in edge)
        },
    )

    return G


def position(G):
    ITERATIONS = 1000
    fa = ForceAtlas2(
        outboundAttractionDistribution=True,
        edgeWeightInfluence=0.2,
    )
    random.seed(0)
    return fa.forceatlas2_networkx_layout(
        G,
        {x: (random.random(), random.random())
         for x in G.nodes},
        ITERATIONS,
    )


def render(G, positions):
    drawing = draw.Drawing(
        HEIGHT,
        WIDTH,
        origin=(0, 0),
    )

    coordinates = list(zip(*positions.values()))
    min_x, max_x = min(coordinates[0]), max(coordinates[0])
    min_y, max_y = min(coordinates[1]), max(coordinates[1])
    positions = {
        node: (
            (pos[0] - min_x) * (WIDTH - PADDING * 2) / (max_x - min_x) +
            PADDING,
            (pos[1] - min_y) * (HEIGHT - PADDING * 2) / (max_y - min_y) +
            PADDING,
        )
        for node, pos in positions.items()
    }

    sizes = defaultdict(lambda: 0)
    max_weight = 0
    for node1, node2 in G.edges:
        weight = G.get_edge_data(node1, node2)['weight']
        sizes[node1] += weight
        sizes[node2] += weight
        if weight > max_weight:
            max_weight = weight
    max_size = max(sizes.values())

    for node1, node2 in sorted(
            G.edges,
            key=lambda x: G.get_edge_data(*x)['weight'],
    ):
        if G.nodes[node1]['type'] != 'person':
            node1, node2 = node2, node1

        title = '{} → {}: ${:,.2f}'.format(
            G.nodes[node1]['label'],
            G.nodes[node2]['label'],
            G.get_edge_data(node1, node2)['weight'] / 100,
        )
        line = draw.Line(
            *positions[node1],
            *positions[node2],
            stroke='#3b3b3b',
            stroke_width=1,
            opacity=(MAX_OPACITY - MIN_OPACITY) *
            (G.get_edge_data(node1, node2)['weight'] / max_weight)**0.5 +
            MIN_OPACITY,
            onclick='alert(\'{}\')'.format(
                html.escape(title.replace('\'', '\\\''))),
        )
        line.appendTitle(title),
        drawing.append(line)

    for node, pos in positions.items():
        title = '{}: ${:,.2f}'.format(
            G.nodes[node]['label'],
            sizes[node] / 100,
        )
        circle = draw.Circle(
            *pos,
            (MAX_SIZE - MIN_SIZE) * (sizes[node] / max_size)**0.5 + MIN_SIZE,
            fill='#84ab3f' if G.nodes[node]['type'] == 'person' else '#ffcfcf',
            stroke_width=1 if G.nodes[node]['type'] == 'person' else 1,
            stroke='white' if G.nodes[node]['type'] == 'person' else '#3b3b3b',
            onclick='alert(\'{}\')'.format(
                html.escape(title.replace('\'', '\\\''))),
        )
        circle.appendTitle(title)
        drawing.append(circle)

    return drawing


def run():
    G = graph()
    positions = position(G)
    svg = render(G, positions)

    svg.saveSvg(os.path.join(settings.MEDIA_ROOT, 'graphs', 'network.svg'))
