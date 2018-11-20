class TestRecord:
    def __init__(self, stream):
        self.footprint = []
        stream.hook = self.footprint.append


def record(s):
    return TestRecord(s)
