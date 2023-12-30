import tqdm
import requests
from json.decoder import JSONDecodeError
from airunner.aihandler.logger import Logger


class DownloadCivitAI:
    cancel_download = False

    @staticmethod
    def get_json(model_id):
        # if model_id == id/name split and get the id
        if "/" in model_id:
            model_id = model_id.split("/")[0]
        url = f"https://civitai.com/api/v1/models/{model_id}"
        response = requests.get(url)
        json = None
        try:
            json = response.json()
        except JSONDecodeError:
            Logger.error(f"Failed to decode JSON from {url}")
            print(response)
        return json

    def download_model(self, url, file_name, size_kb, callback):
        self.download_model_thread(url, file_name, size_kb, callback)

    def download_model_thread(self, url, file_name, size_kb, callback):
        # use tqdm to show progress bar based on size
        # convert size_kb to bytes
        size_kb = size_kb * 1024
        with tqdm.tqdm(total=size_kb, unit="B", unit_scale=True, unit_divisor=1024) as pbar:
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(file_name, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        pbar.update(len(chunk))
                        callback(pbar.n, pbar.total)
                        if self.cancel_download:
                            self.cancel_download = False
                            break

