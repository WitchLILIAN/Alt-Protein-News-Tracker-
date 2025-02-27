from flask import Flask, render_template, request
from datetime import datetime
import sqlite3
import requests
from bs4 import BeautifulSoup
import os
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import httplib2
from googleapiclient.http import build_http
import json
import re

app = Flask(__name__)

# Google Custom Search API 配置
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')  # 从环境变量获取 API 密钥
CUSTOM_SEARCH_ENGINE_ID = os.environ.get('CUSTOM_SEARCH_ENGINE_ID')  # 从环境变量获取搜索引擎 ID

# 验证环境变量是否存在
if not GOOGLE_API_KEY or not CUSTOM_SEARCH_ENGINE_ID:
    raise ValueError("请设置环境变量 GOOGLE_API_KEY 和 CUSTOM_SEARCH_ENGINE_ID")

# 添加代理配置
PROXY_HOST = "127.0.0.1"  # 代理服务器地址（localhost）
PROXY_PORT = "7890"       # HTTP代理端口
PROXY_SOCKS_PORT = "7891" # SOCKS代理端口

# 设置环境变量，让所有HTTP请求都通过代理
os.environ['HTTP_PROXY'] = f'http://{PROXY_HOST}:{PROXY_PORT}'
os.environ['HTTPS_PROXY'] = f'http://{PROXY_HOST}:{PROXY_PORT}'

# API使用计数器
class APICounter:
    def __init__(self, file_path='api_usage.json'):
        self.file_path = file_path
        self.daily_limit = 100
        # 从环境变量获取初始使用次数，如果没有设置则使用0
        self.initial_count = int(os.environ.get('GOOGLE_API_INITIAL_COUNT', '0'))
        print(f"Initial API count from environment: {self.initial_count}")  # 调试输出
        self.load_count()
        
    def get_pst_date(self):
        """获取美国太平洋时间的日期"""
        from datetime import datetime, timezone, timedelta
        pst = timezone(timedelta(hours=-8))  # PST = UTC-8
        return datetime.now(pst).strftime('%Y-%m-%d')
        
    def load_count(self):
        """从文件加载使用次数"""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r') as f:
                    data = json.load(f)
                    current_date = self.get_pst_date()
                    # 如果是新的一天（按PST），重置计数器
                    if data.get('date') != current_date:
                        self.reset_count()
                    else:
                        self.used_count = data.get('count', self.initial_count)
                        self.current_date = current_date
            else:
                self.used_count = self.initial_count  # 使用环境变量中设置的初始值
                self.current_date = self.get_pst_date()
                self.save_count()
        except Exception as e:
            print(f"Error loading count: {e}")
            self.used_count = self.initial_count
            self.current_date = self.get_pst_date()
            self.save_count()
            
    def save_count(self):
        """保存使用次数到文件"""
        try:
            with open(self.file_path, 'w') as f:
                json.dump({
                    'date': self.get_pst_date(),
                    'count': self.used_count
                }, f)
        except Exception as e:
            print(f"Error saving count: {e}")
            
    def reset_count(self):
        """重置计数器"""
        self.used_count = 0
        self.current_date = self.get_pst_date()
        self.save_count()
        
    def get_remaining(self):
        """获取剩余可用次数"""
        # 检查是否需要重置
        current_date = self.get_pst_date()
        if current_date != self.current_date:
            self.reset_count()
        return max(0, self.daily_limit - self.used_count)
    
    def can_make_request(self):
        """检查是否还能继续请求"""
        return self.get_remaining() > 0
    
    def increment(self):
        """增加使用次数"""
        self.used_count += 1
        self.save_count()
        print(f"Current API usage: {self.used_count} (PST date: {self.get_pst_date()})")

# 创建计数器实例
api_counter = APICounter()

def init_db():
    conn = sqlite3.connect('news.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS news
        (title TEXT, url TEXT, date TEXT, source TEXT, snippet TEXT)
    ''')
    conn.commit()
    conn.close()

# 网站映射
site_mapping = {
    'greenqueen': 'greenqueen.com.hk',
    'vegconomist': 'vegconomist.com',
    'agfundnews': 'agfundernews.com',
    'futurealternative': 'futurealternative.com.au',
    'worldbiomarket': 'worldbiomarketinsights.com'
}

# 定义相关领域关键词
RELATED_KEYWORDS = {
    'alternative_protein': '("alternative protein" OR "plant-based protein" OR "cultured meat" OR "cell-based meat" OR "novel protein" OR "future protein")',
    'plant_based': '("plant-based food" OR "plant-based meat" OR "plant-based dairy" OR "plant-based products" OR "vegan food" OR "vegetarian products")',
    'cultivated_meat': '("cultivated meat" OR "cell-based meat" OR "lab-grown meat" OR "cell-cultured" OR "cellular agriculture" OR "cultured protein")',
    'fermentation': '("precision fermentation" OR "biomass fermentation" OR "traditional fermentation" OR "fermentation protein" OR "fermentation technology")',
    'food_policy': '("food regulation" OR "food policy" OR "food safety" OR "regulatory approval" OR "novel food" OR "food standards")'
}

def test_proxy_connection():
    try:
        print("Testing proxy connection...")
        # 先尝试HTTP代理
        http = httplib2.Http(proxy_info=httplib2.ProxyInfo(
            httplib2.socks.PROXY_TYPE_HTTP,
            PROXY_HOST,
            int(PROXY_PORT)
        ))
        try:
            response, content = http.request("https://www.google.com")
            if response.status == 200:
                print("HTTP proxy test successful!")
                return True
        except Exception as e:
            print(f"HTTP proxy test failed: {e}")
            
        # 如果HTTP代理失败，尝试SOCKS代理
        print("Trying SOCKS proxy...")
        http = httplib2.Http(proxy_info=httplib2.ProxyInfo(
            httplib2.socks.PROXY_TYPE_SOCKS5,
            PROXY_HOST,
            int(PROXY_SOCKS_PORT)
        ))
        response, content = http.request("https://www.google.com")
        success = response.status == 200
        print(f"SOCKS proxy test {'successful' if success else 'failed'}")
        return success
    except Exception as e:
        print(f"All proxy tests failed with error: {e}")
        return False

def create_service_with_proxy():
    # 创建支持代理的HTTP客户端
    try:
        # 先尝试HTTP代理
        http = httplib2.Http(proxy_info=httplib2.ProxyInfo(
            httplib2.socks.PROXY_TYPE_HTTP,
            PROXY_HOST,
            int(PROXY_PORT)
        ))
        response, content = http.request("https://www.google.com")
        if response.status != 200:
            raise Exception("HTTP proxy test failed")
    except:
        # 如果HTTP代理失败，尝试SOCKS代理
        http = httplib2.Http(proxy_info=httplib2.ProxyInfo(
            httplib2.socks.PROXY_TYPE_SOCKS5,
            PROXY_HOST,
            int(PROXY_SOCKS_PORT)
        ))
    
    return build('customsearch', 'v1', 
                developerKey=GOOGLE_API_KEY, 
                http=http)

def search_with_google(keyword, site, start_date, end_date, categories=None):
    try:
        print(f"\nAttempting to search {site or 'all web'} for '{keyword}'")
        service = create_service_with_proxy()
        
        # 构建查询
        if site:
            # 特定网站搜索
            query = f'site:{site} {keyword}'
            site_search_filter = 'i'  # 只包含该站点的结果
        else:
            # 全网搜索，使用关键词
            query = f'{keyword} (inurl:article OR inurl:blog OR inurl:post OR inurl:report OR inurl:news)'
            site_search_filter = None  # 不设置 siteSearchFilter
        
        # 添加用户选择的相关领域关键词
        if categories:
            selected_keywords = [RELATED_KEYWORDS[cat] for cat in categories if cat in RELATED_KEYWORDS]
            if selected_keywords:
                query += ' (' + ' OR '.join(selected_keywords) + ')'
        
        # 构建查询参数，使用Google高级搜索参数
        query_params = {
            'q': query,
            'cx': CUSTOM_SEARCH_ENGINE_ID,
            'num': 10,  # 每页结果数
            'sort': 'date',  # 按日期排序
            'dateRestrict': f"d{(datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days}",
            'lr': 'lang_zh|lang_en',  # 限制语言为中文或英文
            'safe': 'active',  # 安全搜索
            'siteSearch': site if site else '',  # 站内搜索
        }
        
        # 仅在特定网站搜索时添加 siteSearchFilter
        if site_search_filter:
            query_params['siteSearchFilter'] = site_search_filter
            
        print(f"Search parameters: {query_params}")
        
        try:
            result = service.cse().list(**query_params).execute()
            print(f"API Response: {result}")
            # 成功请求后更新计数器
            api_counter.increment()
        except Exception as api_error:
            print(f"API call error: {str(api_error)}")
            raise
        
        if 'items' not in result:
            print(f"No items found in response for {site}")
            return []
            
        return result['items']  # 直接返回所有结果
        
    except Exception as e:
        print(f"Search error for {site}: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return []

def get_source_name(url):
    """根据URL确定来源名称"""
    url = url.lower()
    if 'greenqueen.com.hk' in url:
        return 'Green Queen'
    elif 'vegconomist.com' in url:
        return 'Vegconomist'
    elif 'agfundernews.com' in url:
        return 'AgFunder News'
    elif 'futurealternative.com.au' in url:
        return 'Future Alternative'
    elif 'worldbiomarketinsights.com' in url:
        return 'World Bio Market Insights'
    elif 'linkedin.com' in url:
        return 'LinkedIn'
    elif 'instagram.com' in url:
        return 'Instagram'
    elif 'medium.com' in url:
        return 'Medium'
    else:
        return '其他来源'

@app.route('/', methods=['GET', 'POST'])
def index():
    remaining_searches = api_counter.get_remaining()
    
    if request.method == 'POST':
        try:
            # 获取并验证输入参数
            keyword = request.form.get('keyword', '').strip()
            start_date = request.form.get('start_date', '').strip()
            end_date = request.form.get('end_date', '').strip()
            selected_sources = request.form.getlist('sources')
            
            # 如果没有选择任何源，则进行全网搜索
            if not selected_sources:
                selected_sources = ['all']  # 使用特殊标记表示全网搜索
            
            print(f"Input parameters: keyword='{keyword}', start_date='{start_date}', end_date='{end_date}', sources={selected_sources}")
            
            # 验证输入
            if not all([keyword, start_date, end_date]):
                return render_template('index.html', 
                                    error="请填写所有必需的字段",
                                    remaining_searches=remaining_searches)
            
            # 验证日期
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                if end < start:
                    raise ValueError("结束日期早于开始日期")
            except ValueError as e:
                return render_template('index.html', 
                                    error=f"日期格式无效: {str(e)}",
                                    remaining_searches=remaining_searches)
            
            # 获取用户选择的关键词类别
            selected_categories = request.form.getlist('categories') if not selected_sources else None
            
            all_results = []
            for source in selected_sources:
                if source == 'all':
                    # 全网搜索，传入选择的类别
                    results = search_with_google(keyword, '', start_date, end_date, selected_categories)
                    for item in results:
                        try:
                            title = item.get('title', '').strip()
                            url = item.get('link', '').strip()
                            snippet = item.get('snippet', '').strip()
                            
                            # 清理标题和摘要
                            for site_name in ['Green Queen', 'vegconomist', 'AgFunder News']:
                                title = title.replace(f' - {site_name}', '')
                                snippet = snippet.replace(f'... {site_name}', '')
                            
                            # 获取日期
                            date = ''
                            if 'pagemap' in item and 'metatags' in item['pagemap']:
                                date = item['pagemap']['metatags'][0].get('article:published_time', '')[:10]
                            if not date:
                                date_match = re.search(r'\d{4}-\d{2}-\d{2}', snippet)
                                if date_match:
                                    date = date_match.group(0)
                            
                            all_results.append({
                                'title': title,
                                'url': url,
                                'date': date,
                                'source': get_source_name(url),  # 使用新的来源判断函数
                                'snippet': snippet
                            })
                        except Exception as e:
                            print(f"Error processing result: {str(e)}")
                            continue
                elif source in site_mapping:
                    # 特定网站搜索
                    if not api_counter.can_make_request():
                        return render_template('index.html', 
                                            error="搜索过程中达到今日限制",
                                            remaining_searches=0,
                                            results=all_results)
                    
                    api_counter.increment()
                    try:
                        results = search_with_google(keyword, site_mapping[source], start_date, end_date, selected_categories)
                        for item in results:
                            try:
                                title = item.get('title', '').strip()
                                url = item.get('link', '').strip()
                                snippet = item.get('snippet', '').strip()
                                
                                # 清理标题和摘要
                                for site_name in ['Green Queen', 'vegconomist', 'AgFunder News']:
                                    title = title.replace(f' - {site_name}', '')
                                    snippet = snippet.replace(f'... {site_name}', '')
                                
                                # 获取日期
                                date = ''
                                if 'pagemap' in item and 'metatags' in item['pagemap']:
                                    date = item['pagemap']['metatags'][0].get('article:published_time', '')[:10]
                                if not date:
                                    date_match = re.search(r'\d{4}-\d{2}-\d{2}', snippet)
                                    if date_match:
                                        date = date_match.group(0)
                                
                                all_results.append({
                                    'title': title,
                                    'url': url,
                                    'date': date,
                                    'source': get_source_name(url),  # 使用新的来源判断函数
                                    'snippet': snippet
                                })
                            except Exception as e:
                                print(f"Error processing result: {str(e)}")
                                continue
                            
                    except Exception as e:
                        print(f"Error searching {source}: {str(e)}")
                        continue
            
            if not all_results:
                return render_template('index.html', 
                                    error="未找到匹配的结果",
                                    remaining_searches=api_counter.get_remaining())
            
            # 按日期排序
            all_results.sort(key=lambda x: x['date'] if x['date'] else '', reverse=True)
            
            return render_template('index.html', 
                                results=all_results,
                                remaining_searches=api_counter.get_remaining())
                                
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            return render_template('index.html', 
                                error="搜索过程中发生错误，请稍后重试",
                                remaining_searches=api_counter.get_remaining())
    
    return render_template('index.html', remaining_searches=remaining_searches)

if __name__ == '__main__':
    init_db()
    # 在程序启动时测试代理
    print("\n=== Testing proxy configuration ===")
    if test_proxy_connection():
        print("Proxy connection successful!")
    else:
        print("WARNING: Proxy connection failed!")
    # 在程序启动时验证API密钥
    print("\n=== Verifying API configuration ===")
    print(f"API Key length: {len(GOOGLE_API_KEY)}")
    print(f"Search Engine ID length: {len(CUSTOM_SEARCH_ENGINE_ID)}")
    if not GOOGLE_API_KEY or not CUSTOM_SEARCH_ENGINE_ID:
        print("WARNING: API credentials are missing!")
    # 尝试不同的端口，直到找到可用的
    for port in range(5000, 5010):
        try:
            app.run(debug=True, port=port)
            break
        except OSError:
            continue 