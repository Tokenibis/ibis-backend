#!/usr/bin/python3

import re
import json
import time
import requests

from lxml import html

URL = 'https://uwcnm.org/how-we-help/supporting-nonprofits/community-fund/current-grantees?page={}'


def parse(url):
    page = requests.get(url)
    tree = html.fromstring(page.content)
    elements = tree.xpath(
        '//div[@class="view-content"]/div[contains(@class, "views-row")]', )

    results = []
    for i, elm in enumerate(elements):
        try:
            title = elm[1][1][0].text
            description = '/n/n'.join([
                x.text for x in elm[3][0]
                if x.text and not x.text.startswith('(Funded under')
            ])
            results.append({'title': title, 'description': description})
        except IndexError:
            print('Missing title or description on item {} of {}'.format(
                i, len(elements)))
            continue

    return results


def run():
    results = []

    for i in range(10):
        print('Crawling page {}'.format(i))
        results.extend(parse(URL.format(i)))
        time.sleep(2)

    with open('nonprofits.json', 'w') as fd:
        json.dump(results, fd)


if __name__ == '__main__':
    run()
