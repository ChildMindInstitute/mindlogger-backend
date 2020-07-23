import time

from pyfcm import FCMNotification
from concurrent.futures.thread import ThreadPoolExecutor


class FirebaseNotification(FCMNotification):
    def do_request(self, payload, timeout=5):
        response = self.requests_session.post(self.FCM_END_POINT, data=payload, timeout=timeout)
        if 'Retry-After' in response.headers and int(response.headers['Retry-After']) > 0:
            sleep_time = int(response.headers['Retry-After'])
            time.sleep(sleep_time)
            return self.do_request(payload, timeout)
        return response

    def send_request(self, payloads=None, timeout=None):
        self.send_request_responses = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            response = executor.map(self.do_request, payloads)
            executor.map(self.send_request_responses.append, response)
