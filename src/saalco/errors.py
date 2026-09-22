class SaalcoError(Exception):
    exit_code = 2


class CheckFailed(SaalcoError):
    exit_code = 1


class EnvironmentError(SaalcoError):
    exit_code = 3
