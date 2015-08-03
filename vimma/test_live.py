from django.contrib.staticfiles.testing import LiveServerTestCase, StaticLiveServerTestCase
from django.core.urlresolvers import reverse
from django.conf import settings
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class BasicFirefox(StaticLiveServerTestCase):
    """
    Define the unit tests and use Firefox.

    To use another browser, subclass this and override newDriver().
    """

    @staticmethod
    def newDriver():
        """
        Override this method in a subclass to use other browser.
        """
        return webdriver.Firefox()

    @classmethod
    def setUpClass(cls):
        cls.driver = cls.newDriver()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def url(self, path):
        """
        Return the full URL (http://server/path) for the absolute path.

        TODO FIX: The default 'self.live_server_url' (localhost:8081) does not find static/bower_components,
        as they are not part of any application. Directing traffic to Nginx.
        """
        return '{}{}'.format(settings.LIVE_SERVER_URL, path)

    def test_javascript_unit_tests(self):
        self.driver.get(self.url(reverse('test')))
        selector = 'h2#qunit-banner.qunit-fail, h2#qunit-banner.qunit-pass'
        elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        self.assertEqual(elem.get_attribute('class'), 'qunit-pass')


class BasicChromium(BasicFirefox):

    @staticmethod
    def newDriver():
        if os.getenv('TRAVIS') == 'true':
            options = Options()
            options.add_argument('--no-sandbox')
            return webdriver.Chrome(chrome_options=options)

        return webdriver.Chrome()
