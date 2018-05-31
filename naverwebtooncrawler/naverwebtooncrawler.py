"""
Naver Webtoon Crawler

author: Yeojin Kim
author_email: yeojin-dev@gmail.com
"""

import os
import re
from urllib import parse

import requests
from bs4 import BeautifulSoup


class CrawlerAgent:

    @staticmethod
    def crawl(path, url, param=None):
        try:
            if not os.path.exists(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))

            if not os.path.exists(path):
                response = requests.get(url, params=param)
                with open(path, 'xt', encoding='UTF-8') as f:
                    f.write(response.text)

            html = open(path, 'rt', encoding='UTF-8').read()
            soup = BeautifulSoup(html, 'lxml')

            return soup

        except ConnectionError as e:
            print(e)

        except IOError as e:
            print(e)


class Manager:

    home_url = 'http://comic.naver.com/webtoon/weekday.nhn'
    webtoon_base_url = 'http://comic.naver.com/webtoon/list.nhn?'
    episode_base_url = 'http://comic.naver.com/webtoon/detail.nhn?'
    webtoon_list_path = 'naver-webtoon-data/webtoon-list.html'

    webtoon_dict = dict()

    @classmethod
    def search(cls, query):
        query = str(query) if isinstance(query, int) else query

        if not cls.webtoon_dict:
            Manager.update()

        result = list()

        for title, titleId in cls.webtoon_dict.items():
            if query in title or query == titleId:
                result_item = {
                    'title': title,
                    'titleId': titleId
                }
                result.append(result_item)

        return result

    @classmethod
    def make_webtoon(cls, query, all_epi=False):
        result = cls.search(query)

        if len(result) == 0:
            return
        else:
            result = result[0]

        title = result['title']
        webtoon_id = result['titleId']

        webtoon_path = f"naver-webtoon-data/webtoon-{title.replace(' ', '-')}/info.html"
        param = {'titleId': webtoon_id}

        soup = CrawlerAgent.crawl(webtoon_path, cls.webtoon_base_url, param)
        detail = soup.select_one('div.detail > h2')

        info = dict()
        info['title'] = detail.contents[0].strip()
        info['author'] = detail.span.get_text(strip=True)
        info['description'] = soup.select_one('div.detail > p').get_text()

        if all_epi:
            episode_info_list = soup.select('table.viewList > tr')
            episode_list = list()

            for episode_info in episode_info_list:
                if episode_info.get('class'):
                    continue

                episode_dict = dict()

                episode_dict['no'] = \
                    parse.parse_qs(parse.urlsplit(episode_info.select_one('td:nth-of-type(1) a').get('href'))
                                        .query)['no'][0]
                episode_dict['url_thumbnail'] = episode_info.select_one('td:nth-of-type(1) img').get('src')
                episode_dict['title'] = episode_info.select_one('td:nth-of-type(2) a').get_text()
                episode_dict['rating'] = episode_info.select_one('td:nth-of-type(3) strong').get_text()
                episode_dict['created_date'] = episode_info.select_one('td:nth-of-type(4)').get_text()

                episode_element = Episode(webtoon_id, episode_dict)
                episode_list.append(episode_element)

            info['episode_list'] = episode_list

        else:
            info['episode_list'] = list()

        return Webtoon(webtoon_id, info)

    @classmethod
    def update_webtoon(cls, webtoon):
        if isinstance(webtoon, Webtoon):
            return cls.make_webtoon(webtoon.webtoon_id, True)

        else:
            raise ValueError('Argument must be a Webtoon instance.')
            return

    @classmethod
    def download_episode(cls, webtoon, min_no=1, max_no=1, all_epi=False):
        if not isinstance(webtoon, Webtoon):
            raise ValueError('Argument must be a Webtoon instance.')
            return

        # episode_list가 빈 리스트일 경우
        if len(webtoon.episode_list) == 0:
            print('Episode list is empty.')
            return

        else:
            max_num = int(webtoon.episode_list[0].no)

        if max_no > max_num or min_no < 1 or min_no > max_no:
            raise ValueError('Min_no or max_no value is wrong.')
            return

        if all_epi:
            max_no = max_num
            min_no = 1

        for no in range(min_no, max_no + 1):
            episode_dir = f"naver-webtoon-data/webtoon-{webtoon.title.replace(' ', '-')}/{str(no)}/"
            param = {'titleId': webtoon.webtoon_id, 'no': str(no)}

            soup = CrawlerAgent.crawl(episode_dir + 'episode_info.html', cls.episode_base_url, param)
            imgs = soup.select('div.wt_viewer > img')

            header = {'Referer': cls.episode_base_url + parse.urlencode(param)}

            try:
                for img in imgs:
                    image_file_path = episode_dir + img['id'] + '.jpg'
                    image_file_data = requests.get(img['src'], headers=header, params=param).content
                    open(image_file_path, 'wb').write(image_file_data)

            except ConnectionError as e:
                print(e)

            except IOError as e:
                print(e)

    @classmethod
    def update(cls):
        extract_id_regex = re.compile('webtoon/(\d+)')

        soup = CrawlerAgent.crawl(cls.webtoon_list_path, cls.home_url)
        imgs = soup.select('div.thumb > a > img:nth-of-type(1)')

        for img in imgs:
            title = img['title']
            webtoon_id = re.search(extract_id_regex, img['src']).group(1)
            cls.webtoon_dict[title] = webtoon_id


class Webtoon:

    def __init__(self, webtoon_id, info):

        self.webtoon_id = webtoon_id

        # info.keys() = ['title', 'author', 'description', 'episode_list']
        vars(self).update(info)


class Episode:

    def __init__(self, webtoon_id, info):

        self.webtoon_id = webtoon_id

        # info.keys() = ['no', 'url_thumbnail', 'title', 'rating', 'created_date']
        vars(self).update(info)

    @property
    def url(self):
        data = {'titleId': self.webtoon_id, 'no': self.no}
        return Manager.webtoon_base_url + parse.urlencode(data)

