import time
import logging
import mysql.connector
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

logging.basicConfig(level=logging.INFO)

# MySQL 資料庫連接設置
db_connection = mysql.connector.connect(
    host="127.0.0.1",
    port="3306",
    user="root",
    password="",
    database="news_db"
)

cursor = db_connection.cursor()

# 建立 articles 資料表（如果尚未存在）
cursor.execute("""
CREATE TABLE IF NOT EXISTS articles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255),
    content TEXT,
    url VARCHAR(255)
)
""")

# 使用 webdriver_manager 自動下載並管理 ChromeDriver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)


# 打開新聞網站
driver.get('https://technews.tw/')
time.sleep(3)

# 找到首頁的所有文章標題連結
articles = driver.find_elements(By.XPATH, '//*[@class="img"]/a | //*[@class="spotlist"]/a | //*[@class="entry-title"]/a')

# 儲存所有文章的連結和標題，但只保留唯一的 href
seen_hrefs = set()
article_data = []

for article in articles:
    href = article.get_attribute('href')
    if href not in seen_hrefs:
        seen_hrefs.add(href)
        article_data.append((article.text, href))

# 遍歷每一篇文章的連結
for article_title, article_link in article_data:
    # 點擊文章連結進入詳細頁面
    driver.get(article_link)

    time.sleep(3)

    try:
        content = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@class="indent"]'))
        )
        print(f"Title: {article_title}")
        print(f"Content: {content.text}")

        # 清除上一次查詢的結果
        cursor.reset()

        # 檢查資料庫中是否已經存在具有相同標題的文章
        cursor.execute("SELECT id FROM articles WHERE title = %s", (article_title,))
        result = cursor.fetchone()
        
        if result is None:
            # 將文章標題、內容和 URL 存入 MySQL 資料庫
            cursor.execute("""
                INSERT INTO articles (title, content, url) 
                VALUES (%s, %s, %s)
            """, (article_title, content.text, article_link))
            db_connection.commit()
        else:
            print(f"Article with title '{article_title}' already exists in the database.")

    except TimeoutException:
        print(f"Element not found for article '{article_title}' within the given time")

    # 回到首頁
    driver.get('https://technews.tw/')

    # 等待首頁加載
    time.sleep(3)

# 關閉瀏覽器
driver.quit()

# 關閉資料庫連接
cursor.close()
db_connection.close()
