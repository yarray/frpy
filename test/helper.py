class TestRecord:
    def __init__(self, stream):
        self.footprint = []
        if stream() is not None:
            self.footprint.append(stream())
        stream.hook = self.footprint.append


def record(s):
    return TestRecord(s)
