class ExtensionsMixin:
    active_extensions = []  # TODO: extensions

    def call_pipe_extension(self, **kwargs):
        """
        This calls the call_pipe method on all active extensions
        :param kwargs:
        :return:
        """
        for extension in self.active_extensions:
            self.pipe = extension.call_pipe(self.options, self.model_base_path, self.pipe, **kwargs)
        return self.pipe