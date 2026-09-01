import scrapy
from scrapy.selector import Selector
from datetime import datetime
import re


class CctvSpider(scrapy.Spider):
    # 爬虫名字，后面运行要用
    name = 'cctv'
    # 只允许抓取央视网域名下的页面
    allowed_domains = ['tv.cctv.com']
    # 新闻联播栏目主页，从这里获取当天所有新闻的链接
    start_urls = ['https://tv.cctv.com/lm/xwlb/index.shtml']

    def parse(self, response):
        """
        解析栏目主页，提取所有新闻的标题和链接
        """
        # 栏目主页上，每条新闻都放在 <li> 标签里，class 包含 'items'
        news_items = response.xpath('//li[contains(@class, "items")]')
        
        for item in news_items:
            # 提取新闻标题
            title = item.xpath('.//a/text()').get()
            # 提取新闻详情页链接
            link = item.xpath('.//a/@href').get()
            
            # 如果标题或链接为空，跳过这条
            if not title or not link:
                continue
            
            # 如果链接是相对路径，补全为完整URL
            if not link.startswith('http'):
                link = response.urljoin(link)
            
            # 访问详情页，把标题和链接传过去，回调 parse_detail 处理页面内容
            yield scrapy.Request(
                url=link,
                callback=self.parse_detail,
                meta={'title': title.strip(), 'link': link}
            )

    def parse_detail(self, response):
        """
        解析新闻详情页，提取正文文字稿
        """
        title = response.meta['title']
        link = response.meta['link']
        
        # 正文通常放在 class 包含 'content' 或 'text' 的 div 里
        # 央视网详情页的正文一般在 class="content_area" 或类似容器中
        content_div = response.xpath('//div[contains(@class, "content")]')
        if not content_div:
            # 如果没找到，尝试其他常见的正文容器
            content_div = response.xpath('//div[contains(@class, "text")]')
        if not content_div:
            content_div = response.xpath('//div[contains(@class, "article")]')
        
        # 提取正文中的所有段落文本
        if content_div:
            paragraphs = content_div.xpath('.//p/text()').getall()
            # 过滤掉空行和纯空白行，合并成完整正文
            body = '\n'.join([p.strip() for p in paragraphs if p.strip()])
        else:
            # 如果上述选择器都没匹配到，尝试获取页面所有文本（备用方案）
            all_text = response.xpath('//body//text()').getall()
            body = '\n'.join([t.strip() for t in all_text if t.strip()])
        
        # 如果正文为空，尝试从包含"央视网消息"的段落提取
        if not body:
            msg_paragraphs = response.xpath('//p[contains(text(), "央视网消息")]/text()').getall()
            if msg_paragraphs:
                body = '\n'.join([p.strip() for p in msg_paragraphs if p.strip()])
        
        # 输出抓取结果
        yield {
            'title': title,
            'link': link,
            'body': body,
            'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
