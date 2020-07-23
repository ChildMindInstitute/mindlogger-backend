from pyfcm import FCMNotification
from concurrent.futures.thread import ThreadPoolExecutor


class FirebaseNotification(FCMNotification):
    def send_request(self, payloads=None, timeout=None):
        self.send_request_responses = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            response = executor.map(self.do_request, payloads, (timeout,))
            executor.map(self.send_request_responses.append, response)
