# unit tests
import pytest
from girderformindlogger.constants import REPROLIB_CANONICAL
from girderformindlogger.utility.jsonld_expander import dereference

testInput = {
    "http://schema.org/about": [
        {
            "@language": "en",
            "@value": "reprolib:protocols/ema-hbn/README.md"
        }
    ]
}

testOutput = {
    "http://schema.org/about": [
        {
            "@language": "en",
            "@value": "{}protocols/ema-hbn/README.md".format(
                REPROLIB_CANONICAL
            )
        }
    ]
}

@pytest.mark.parametrize(
    "args",
    [(testInput, testOutput)]
)
def testDereference(args):
    assert dereference(testInput)==testOutput, 'Dereferencing failed.'
