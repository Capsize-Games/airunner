from airunner.app import App


class SocketServer(App):
    def __init__(
        self,
        *args,
        # host="",
        # port="",
        # keep_alive="",
        # packet_size=""
    ):
        super().__init__(*args)

    def run(self):
        pass
