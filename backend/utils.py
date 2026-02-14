class SilentLogger:
    def debug(self, msg):
        pass
    def warning(self, msg):
        if "No supported JavaScript runtime" not in msg:
            print(msg)
    def error(self, msg):
        print(msg)