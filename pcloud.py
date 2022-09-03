"""https://www.youtube.com/watch?v=Ven-pqwk3ec"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import aiohttp
import re
import json
import os


service = Service(executable_path=os.environ['CHROMEDRIVER_PATH'])

options = webdriver.ChromeOptions()
options.binary_location = os.environ['GOOGLE_CHROME_BIN']
options.add_argument('--headless')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--no-sandbox')


class PyCloud:


  def __init__(self):
    
    self.driver = webdriver.Chrome(service=service, options=options)
    self.driver.get('https://my.pcloud.com/#page=login')

    # Sign in
    WebDriverWait(self.driver, 60).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.login-input-email'))).send_keys(os.environ['STORAGE_EMAIL'])
    self.driver.find_element('css selector', '.login-input-password').send_keys(os.environ['STORAGE_PASSWORD'])
    self.driver.find_element('css selector', '.butt.submitbut').click()


  async def _get_download_link(self, filename):

    files = self.driver.find_elements('css selector', '.file')
    file = next(file for file in files if file.find_element('css selector', '.filename').text == filename)
    file.find_element('css selector', '.share-opts').click()
    print('AAAAAAAAAAAAAAAAAA')
    popup = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.bLMYbk > div')))
    publink = popup.find_element('css selector', 'input').get_property('value')
    popup.find_element('css selector', '.kOcgKK').click()  # Close popup
    print('BBBBBBBBBBBBBBBBBBBBB')
    async with aiohttp.ClientSession() as s:
      async with s.get(publink) as r:
        publink_html = await r.text()
    print('CCCCCCCCCCCCCCCCCCCCCCCC')
    publink_data = json.loads(re.findall(r'var publinkData = .*?;', publink_html, flags=re.DOTALL)[0][18:-1])
    return publink_data['downloadlink']


  async def get_download_link(self, filename):
    """Retrieve a download link that matches filename"""
    try:
      return await self.get_download_link(filename)
    except: 
      self.__init__()
      return await self.get_download_link(filename)
    
