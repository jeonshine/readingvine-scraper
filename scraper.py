import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from oauth2client.service_account import ServiceAccountCredentials
import gspread

import time

def connect_gspread(file_name):

    scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive',
    ]
    json_file_name = 'lxper.json'
    credentials = ServiceAccountCredentials.from_json_keyfile_name(json_file_name, scope)
    gc = gspread.authorize(credentials)
    sheets = gc.open(file_name)

    return sheets

def write_gspread(worksheet, index, result):

    last_alphabet = chr(65 + len(result))

    try:
        worksheet.update(f"A{index}:{last_alphabet}{index}", [result])
    except:
        # over 50000 string in one cell ==> error
        # allow one data writing per a sec
        print(f"{index} index got error while gspread writing")

def init_browser(url, version):

    # option for browser
    browser = uc.Chrome(version_main=version, suppress_welcome=True)
    browser.maximize_window()
    browser.implicitly_wait(10)

    # init browser
    browser.get(url)
    time.sleep(2)

    return browser

def get_last_page(browser):
    try:
        return int(browser.find_elements(By.XPATH, '//div[@class="pagination"]/a')[-2].text)
    except:
        print("no pagination element load!")

def login(browser):
    login_btn = browser.find_element(By.XPATH, '//a[@data-label="Login"]')
    login_btn.click()

    email_input = browser.find_element(By.XPATH, '//input[@id="user_email"]')
    password_input = browser.find_element(By.XPATH, '//input[@id="user_password"]')

    email_input.send_keys("hojongjeon@lxper.com")
    password_input.send_keys("hojongjeon@lxper.com")
    password_input.send_keys(Keys.RETURN)

def scrape(browser, content_links, worksheet, content_count):

    for index, content_link in enumerate(content_links):
        
        result = []

        time.sleep(1)
        browser.get(content_link)

        # start scrape [meta data]
        link = browser.current_url

        passages_text_container = browser.find_element(By.XPATH, '//div[@class="passage-text-container"]')
        meta_data_container = browser.find_element(By.XPATH, '//div[@class="category-values"]')
        
        try:
            title = passages_text_container.find_element(By.XPATH, './h4[@class="hidden-print"]').text
        except:
            title = ""

        try:
            author = passages_text_container.find_element(By.XPATH, './h5[@class="hidden-print"]').text
        except:
            author = ""

        try:
            words = meta_data_container.find_element(By.XPATH, './/p/strong[contains(text(), "Words:")]//following-sibling::a').text
        except:
            words = ""

        try:
            grade = ""
            grades = meta_data_container.find_elements(By.XPATH, './/p/strong[contains(text(), "Grades:")]//following-sibling::a')

            for g in grades:
                grade += f"{g.text } " if g != grades[-1] else g.text
                
        except:
            grade = ""

        try:
            topic = ""
            topics = meta_data_container.find_elements(By.XPATH, './/p/strong[contains(text(), "Topics:")]//following-sibling::a')

            for t in topics:
                topic += f"{t.text} / " if t != topics[-1] else t.text
                
        except:
            topic = ""

        try:    
            genre = ""
            genres = meta_data_container.find_elements(By.XPATH, './/p/strong[contains(text(), "Genres:")]//following-sibling::a')

            for g in genres:
                genre += f"{g.text } " if g != genres[-1] else g.text
                
        except:
            genre = ""

        try:
            lexile_range = meta_data_container.find_element(By.XPATH, './/p/strong[contains(text(), "Lexile Range:")]//following-sibling::a').text
        except:
            lexile_range = ""

        try:
            lexile_measure = meta_data_container.find_elements(By.XPATH, './/p')[-3].text.split(":")[-1].strip()
        except:
            lexile_measure = ""

        try:
            text = passages_text_container.find_elements(By.XPATH, './*')[-1].text
        except:
            text = ""
        
        result.extend([
            link, title, author, words, grade, topic, genre, lexile_range, lexile_measure, text
        ])
        
        write_gspread(worksheet, content_count+index+1, result)

        print(f"{index+1} / {len(content_links)} done")

if  __name__  ==  "__main__" :

    # google sperad 
    GSPREAD = "Reading Text Scraping"
    RETRY_SHEET = "retry"
    PASSAGES_SHEET = "ReadingVine passages"
    sheets = connect_gspread(GSPREAD)
    worksheet = sheets.worksheet(PASSAGES_SHEET)
    retry_worksheet = sheets.worksheet(RETRY_SHEET)

    # ReadingVine Url
    ROOT_URL = "https://www.readingvine.com"

    # chorme version
    CHROME_VERSION = 103
    browser = init_browser(f"{ROOT_URL}/search?searchable_type=Passage", CHROME_VERSION)

    # last page 
    last_page = get_last_page(browser)

    # some contents are not accessed without login
    login(browser)

    # re-try 
    content_links = retry_worksheet.col_values(1)
    if content_links:
        scrape(browser, content_links, retry_worksheet, content_count=0)
        
    # start page loop
    content_count = 0
    for page in range(1, last_page+1):
        print(f"========== {page} / {last_page} page  start ==========")

        time.sleep(2)
        browser.get(f"{ROOT_URL}/search?page={page}&searchable_type=Passage")

        contents = browser.find_elements(By.XPATH, '//div[@class="row passage"]')
        content_links = [content.find_element(By.XPATH, './/a').get_attribute("href") for content in contents]

        scrape(browser, content_links, worksheet, content_count)
        content_count += len(content_links)

        print(f"========== {page} / {last_page} page finish ==========") 

    browser.quit()

    print("debug")