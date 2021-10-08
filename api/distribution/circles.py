import os
import html
import json
import math
import drawSvg as draw
import ibis.models as models

from tqdm import tqdm
from django.conf import settings
from graphql_relay.node.node import from_global_id, to_global_id
from ibis.schema import UserNode, GrantNode, GrantDonationNode

HORIZON = 4092  # number of historical transactions to remember
EPSILON = 1e-4  # small error used for geometric float calculations
INITIAL = 16  # initial threshold to set scope optimizer

TIME = 20  # approximate number of seconds to run SVG animation
GD_TIME = 2  # number of seconds for single grantdonation to appear
HEIGHT, WIDTH, PADDING = 1080, 1080, 50  # dimensions of SVG image
RADIUS_MODIFIER = 0.95  # shrink SVG circles by this number
X_LIGHT, Y_LIGHT = 0.25, 0.5  # controls tilt of lighting source

DIR = os.path.join(settings.MEDIA_ROOT, 'circles')


def _distance(p1, p2=(0, 0)):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def _radius(volume):
    return math.sqrt(abs(volume) / math.pi)


def _propose(circles, radius, anchor):
    def _candidates(c1, c2, r, anchor):
        x0, y0, r0 = c1
        x1, y1, r1 = c2

        r0 += r
        r1 += r

        d = _distance((x0, y0), (x1, y1))

        # no overlap
        if d > r0 + r1:
            return []

        # a contains b
        if d < abs(r0 - r1):
            return []

        # a is b
        if d == 0 and r0 == r1:
            return []

        # intersects; return one good candidate
        else:
            a = (r0**2 - r1**2 + d**2) / (2 * d)
            h = math.sqrt(r0**2 - a**2 + EPSILON)
            x2 = x0 + a * (x1 - x0) / d
            y2 = y0 + a * (y1 - y0) / d
            x3 = x2 + h * (y1 - y0) / d
            y3 = y2 - h * (x1 - x0) / d

            x4 = x2 - h * (y1 - y0) / d
            y4 = y2 + h * (x1 - x0) / d

            # handle corner case where intersections are equadistant
            if abs(_distance((x3, y3)) - _distance((x4, y4))) < EPSILON:
                return [(x3, y3, r), (x4, y4, r)]

            return [
                max(
                    [(x3, y3, r), (x4, y4, r)],
                    key=lambda d: _distance(d, anchor),
                )
            ]

    def _valid(c1, c2):
        x0, y0, r0 = c1
        x1, y1, r1 = c2

        d = _distance((x0, y0), (x1, y1)) + EPSILON

        # collides
        if d < r0 + r1:
            return False

        return True

    result = []
    for i, c1 in enumerate(circles):
        for c2 in circles[i + 1:]:
            for candidate in _candidates(c1, c2, radius, anchor):
                is_valid = True
                for c3 in circles:
                    if not _valid(candidate, c3):
                        is_valid = False
                        break

                if is_valid:
                    result.append(candidate)

    return result


def _choose(candidates, anchor):
    return min(candidates, key=lambda c: _distance(c, anchor))


def calculate(circles={}):

    data = models.GrantDonation.objects.order_by(
        'donation__created',
        'grant__created',
        'id',
    )

    if not circles:
        circles['grants'] = [{
            'id':
            to_global_id(GrantNode.__name__, data[0].grant.id),
            'circle': (
                0,
                0,
                _radius(data[0].grant.amount),
            ),
            'anchor':
            '',
        }]

        circles['grantdonations'] = [{
            'id':
            to_global_id(GrantDonationNode.__name__, data[0].id),
            'circle': (
                0,
                _radius(data[0].amount) + circles['grants'][0]['circle'][2],
                _radius(data[0].amount),
            ),
            'anchor':
            to_global_id(GrantNode.__name__, data[0].grant.id),
        }]

    lookup = {x['id']: i for i, x in enumerate(circles['grants'])}

    def _make_circle(amount, anchor_id):
        radius = _radius(amount)
        limit = radius * INITIAL
        anchor = circles['grants'][lookup[anchor_id]]

        while True:
            scope = [
                c['circle'] for c in circles['grantdonations'][-HORIZON:] +
                list(circles['grants'][lookup[a]] for a in set([
                    x['anchor'] for x in circles['grantdonations'][-HORIZON:]
                ] + [anchor_id])) if _distance(anchor['circle'], c['circle']) -
                c['circle'][2] - anchor['circle'][2] < limit + EPSILON
            ]

            candidates = _propose(scope, radius, anchor['circle'])

            try:
                circle = _choose(candidates, anchor['circle'])
                assert _distance(
                    circle,
                    anchor['circle'],
                ) - anchor['circle'][2] + radius < limit
            except (AssertionError, ValueError):
                limit *= 2
                continue

            return circle

    for d in tqdm(data[len(circles['grantdonations']):]):
        id = to_global_id(GrantDonationNode.__name__, d.id)
        grant_id = to_global_id(GrantNode.__name__, d.grant.id)

        if grant_id not in lookup:
            circles['grants'].append({
                'id':
                grant_id,
                'circle':
                _make_circle(
                    d.grant.amount,
                    circles['grants'][-1]['id'],
                ),
                'anchor':
                circles['grants'][-1]['id'],
            })
            lookup[grant_id] = len(circles['grants']) - 1

        circles['grantdonations'].append({
            'id':
            id,
            'circle':
            _make_circle(
                d.amount,
                circles['grants'][lookup[grant_id]]['id'],
            ),
            'anchor':
            circles['grants'][lookup[grant_id]]['id'],
        })

    return circles


def render(circles, animate=False):
    raw = (
        min(c['circle'][0] - c['circle'][2]
            for c in circles['grants'] + circles['grantdonations']),
        max(c['circle'][0] + c['circle'][2]
            for c in circles['grants'] + circles['grantdonations']),
        min(c['circle'][1] - c['circle'][2]
            for c in circles['grants'] + circles['grantdonations']),
        max(c['circle'][1] + c['circle'][2]
            for c in circles['grants'] + circles['grantdonations']),
    )

    scale = max(
        (raw[1] - raw[0]) / (WIDTH - PADDING * 2),
        (raw[3] - raw[2]) / (HEIGHT - PADDING * 2),
    )

    box = tuple(x / scale for x in raw)

    drawing = draw.Drawing(
        WIDTH,
        HEIGHT,
        origin=(
            box[0] - (WIDTH - (box[1] - box[0])) / 2,
            box[2] - (HEIGHT - (box[3] - box[2])) / 2,
        ),
    )

    first = models.GrantDonation.objects.get(
        id=from_global_id(circles['grantdonations'][0]['id'])[1]).donation
    speed = TIME / (models.GrantDonation.objects.get(
        id=from_global_id(circles['grantdonations'][-1]['id'])
        [1]).donation.created - first.created).total_seconds()

    def _time(x, base=first, extra=0):
        return '{}s'.format(0.01 + extra +
                            (x.created - base.created).total_seconds() * speed)

    for circle in circles['grantdonations']:
        obj = models.GrantDonation.objects.get(
            id=from_global_id(circle['id'])[1])
        x = circle['circle'][0] / scale
        y = circle['circle'][1] / scale
        r = circle['circle'][2] / scale * RADIUS_MODIFIER

        gradient = draw.RadialGradient(
            x + r * X_LIGHT,
            y + r * Y_LIGHT,
            r,
        )
        gradient.addStop(0.1, '#ffffff')
        gradient.addStop(0.9, '#51780C')

        title = '{}{} → {} (${:.2f}): {}'.format(
            '' if obj.donation.funded_by.count() == 1 else '[{}/{}] '.format(
                obj.donation.funded_by.order_by('created').filter(
                    created__lte=obj.grant.created).count(),
                obj.donation.funded_by.count(),
            ),
            obj.donation.user,
            obj.donation.target,
            obj.amount / 100,
            obj.donation.description,
        )
        circle = draw.Circle(
            x,
            y,
            0 if animate else r,
            fill=gradient,
            id=to_global_id(GrantDonationNode.__name__, obj.id),
            amount=obj.amount,
            user=to_global_id(UserNode.__name__, obj.donation.user.id),
            target=to_global_id(UserNode.__name__, obj.donation.target.id),
            grant=to_global_id(GrantNode.__name__, obj.grant.id),
            onclick='alert(\'{}\')'.format(
                html.escape(title.replace('\'', '\\\''))),
        )
        circle.appendTitle(title)
        if animate:
            circle.appendAnim(
                draw.Animate(
                    'r',
                    '{}s'.format(GD_TIME),
                    '0;{}'.format(r),
                    begin=_time(obj.donation),
                    fill='freeze',
                ))
        drawing.append(circle)

    for circle in circles['grants']:
        obj = models.Grant.objects.get(id=from_global_id(circle['id'])[1])
        x = circle['circle'][0] / scale
        y = circle['circle'][1] / scale
        r = circle['circle'][2] * RADIUS_MODIFIER * sum(
            z.amount for z in obj.grantdonation_set.all()) / obj.amount / scale

        gradient = draw.RadialGradient(
            x if animate else x + r * X_LIGHT,
            y if animate else y + r * Y_LIGHT,
            0 if animate else r,
        )
        gradient.addStop(0.1, '#ffffff')
        gradient.addStop(0.9, '#bbbbbb')

        title = '{} → : ${:.2f}'.format(
            obj.name,
            obj.amount / 100,
        )

        circle = draw.Circle(
            x,
            y,
            0 if animate else r,
            fill=gradient,
            id=to_global_id(GrantNode.__name__, obj.id),
            description=html.escape(title),
            onclick='alert(\'{}\')'.format(
                html.escape(title.replace('\'', '\\\''))),
        )
        circle.appendTitle(title)
        if animate:
            first_donation = obj.funded.order_by('created').first()
            last_donation = obj.funded.order_by('created').last()
            circle.appendAnim(
                draw.Animate(
                    'r',
                    _time(last_donation, first_donation, GD_TIME),
                    '0;{}'.format(r),
                    begin=_time(first_donation),
                    fill='freeze',
                ))
            gradient.appendAnim(
                draw.Animate(
                    'r',
                    _time(last_donation, first_donation, GD_TIME),
                    '0;{}'.format(r),
                    begin=_time(first_donation),
                    fill='freeze',
                ))
            gradient.appendAnim(
                draw.Animate(
                    'cx',
                    _time(last_donation, first_donation, GD_TIME),
                    '{};{}'.format(x, x + r * X_LIGHT),
                    begin=_time(first_donation),
                    fill='freeze',
                ))
            gradient.appendAnim(
                draw.Animate(
                    'cy',
                    _time(last_donation, first_donation, GD_TIME),
                    '{};{}'.format(-y, -y - r * Y_LIGHT),
                    begin=_time(first_donation),
                    fill='freeze',
                ))

        drawing.append(circle)

    return drawing


def run():
    os.makedirs(DIR, exist_ok=True)

    try:
        with open(os.path.join(DIR, 'data.json')) as fd:
            data = json.load(fd)

        if all([
                len(data['grantdonations']) ==
                models.GrantDonation.objects.count(),
                os.path.exists(os.path.join(DIR, 'static.svg')),
                os.path.exists(os.path.join(DIR, 'dynamic.svg')),
        ]):
            return

        data = calculate(data)
    except FileNotFoundError:
        data = calculate()

    with open(os.path.join(DIR, 'data.json'), 'w') as fd:
        json.dump(data, fd, indent=2)

    render(data, animate=False).saveSvg(os.path.join(DIR, 'static.svg'))
    render(data, animate=True).saveSvg(os.path.join(DIR, 'dynamic.svg'))
