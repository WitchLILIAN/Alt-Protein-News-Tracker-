# Alt-Protein-News-Tracker-

Alt Protein News Tracker is a tool for searching and tracking news in the alternative protein food industry. Users can search for articles, blogs, posts, and reports on specific vegan websites or across the web using keywords and date ranges. The tool supports English and Chinese languages and offers an intuitive user interface. The project is hosted on GitHub Pages, allowing users to access it online. Click to track Alt Protein.

Alt Protein News Tracker 是一个用于搜索和跟踪替代蛋白行业新闻的工具。用户可以通过关键词和日期范围搜索特定网站或全网的相关文章、博客、帖子和报告。该工具支持中英双语搜索。通过GitHub Pages托管提供网页服务，用户可以通过网络访问一键查询新蛋白行业新闻。

## 功能特点 / Features

- **多语言支持 / Multi-language Support**: 支持中文和英文搜索。
- **高级搜索 / Advanced Search**: 使用 Google 高级搜索语法+url格式过滤结果。
- **自定义网站 / Custom Websites**: 支持特定新蛋白行业新闻媒体网站的新闻搜索。
- **全网搜索 / Global Search**: 可以在全网范围内搜索相关内容。
- **用户友好的界面 / User-friendly Interface**: 提供简洁直观的用户界面。
- **在线访问 / Online Access**: 项目托管在 GitHub Pages 上，用户可以通过网络访问。


## 安装 / Installation

1. 克隆此仓库 / Clone this repository:
   ```bash
   git clone https://github.com/yourusername/alt-protein-news-tracker.git
   cd alt-protein-news-tracker
   ```

2. 安装依赖 / Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. 设置环境变量 / Set environment variables:
   - `GOOGLE_API_KEY`: 你的 Google API 密钥 / Your Google API key
   - `CUSTOM_SEARCH_ENGINE_ID`: 你的自定义搜索引擎 ID / Your custom search engine ID
   - `GOOGLE_API_INITIAL_COUNT`: 初始使用次数 / Initial usage count

4. 运行应用 / Run the application:
   ```bash
   python app.py
   ```

## 使用 / Usage

- 访问 `http://localhost:5000` 在本地运行应用。
- 输入关键词和日期范围进行搜索。
- 选择特定网站或全网搜索。
- 当前版本每日搜索上限为100次，搜索入口实时显示剩余搜索次数，美国太平洋时间午夜0点重置

## 贡献 / Contributing

欢迎贡献者！请提交 pull request 或报告问题。

## 许可证 / License

MIT License. See `LICENSE` for more information.

## 联系 / Contact

- **作者 / Author**: WU QINLIN
- **电子邮件 / Email**: wuqinlinlilian@gmail.com
