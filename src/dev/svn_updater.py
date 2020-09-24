"""A script for committing the project into a Subversion repository.
"""

import os

from src import about
from src.dev import documentation
from src.tools import path_tools as pt
from src.tools.subversion import SVNRepository

def run(updateDocs=False, message=None):
    """Run the update tool."""
    
    if updateDocs:
        documentation.compileDocumentation(about.getVersion())
    about.writeChangelog(os.path.join(pt.unrel(), 'CHANGES'))
    repo = SVNRepository(pt.unrel())
    repo.markUnknowns()
    if message is None:
        message = about.getLatestMessage()
#     print(message)
    repo.commit(message)
    print('Finished')
    
if __name__ == '__main__':
    run(False)