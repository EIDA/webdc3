import sys
import unittest

class WITestRunner(object):

    def __init__(self, outStream=sys.stderr, mode=1):
        "Save the stream where the output will be printed"

        self.mode = mode
        if mode:
            # Colours escape command
            self.HEADER = '\033[95m'
            self.OKBLUE = '\033[94m'
            self.OKGREEN = '\033[92m'
            self.WARNING = '\033[93m'
            self.FAIL = '\033[91m'
            self.ENDC = '\033[0m'
        else:
            # Colours escape command
            self.HEADER = ''
            self.OKBLUE = ''
            self.OKGREEN = ''
            self.WARNING = ''
            self.FAIL = ''
            self.ENDC = ''

        self.outStream = outStream
        self.write(self.HEADER + '\nRunning test...\n' + self.ENDC)

    def write(self, message):
        """Redirect output to the stream"""
        self.outStream.write(message)

    def run(self, test):
        """Run the given test case"""
        result = WITestResult(self, self.mode)
        test(result)

        if len(result.failures) + len(result.errors) > 0:
            self.write(self.HEADER + '\nError/Failure details\n' + self.ENDC)
            result.printErrors()

        run = result.testsRun
        return result


class WITestResult(unittest.TestResult):
    """A test result class that prints in colours to the console
    """

    def __init__(self, testRunner, mode=1):
        unittest.TestResult.__init__(self)

        if mode:
            # Colours escape command
            self.HEADER = '\033[95m'
            self.OKBLUE = '\033[94m'
            self.OKGREEN = '\033[92m'
            self.WARNING = '\033[93m'
            self.FAIL = '\033[91m'
            self.ENDC = '\033[0m'
        else:
            # Colours escape command
            self.HEADER = ''
            self.OKBLUE = ''
            self.OKGREEN = ''
            self.WARNING = ''
            self.FAIL = ''
            self.ENDC = ''

        self.testRunner = testRunner

    def startTest(self, test):
        unittest.TestResult.startTest(self, test)
        self.testRunner.write('Checking %s... ' % test.shortDescription())

    def addSuccess(self, test):
        unittest.TestResult.addSuccess(self, test)
        self.testRunner.write('[' + self.OKGREEN + 'OK' + self.ENDC + ']\n')

    def addError(self, test, err):
        unittest.TestResult.addError(self, test, err)
        self.testRunner.write('[' + self.WARNING + 'ERROR' + self.ENDC + ']\n')

    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err)
        self.testRunner.write('[' + self.FAIL + 'FAIL' + self.ENDC + ']\n')

    def printErrors(self):
        self.printErrorList('Error', self.errors)
        self.printErrorList('Failure', self.failures)

    def printErrorList(self, errorType, errors):
        for test, err in errors:
            self.testRunner.write('%s checking %s\n' %
                                    (errorType, test.shortDescription()))
            self.testRunner.write((self.WARNING + '    %s' + self.ENDC) % err.splitlines(True)[-1])
