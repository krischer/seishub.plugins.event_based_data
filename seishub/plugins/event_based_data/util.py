#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shared utility function.

:copyright:
    Lion Krischer (krischer@geophysik.uni-muenchen.de), 2012
:license:
    GNU Lesser General Public License, Version 3
    (http://www.gnu.org/copyleft/lesser.html)
"""
from seishub.core.exceptions import DuplicateObjectError

import hashlib

from table_definitions import FilepathsTable


def check_if_file_exist_in_db(data, env):
    """
    Checks if a file with the same md5 checksum exists in the filepaths table.
    Raises an appropriate error if it does not exist. Otherwise the md5 hash is
    returned.

    :type data: String
    :param data: The file as a string.
    :type env: seishub.core.Environment
    :param env: The current SeisHub environment
    """
    md5_hash = hashlib.md5(data).hexdigest()

    session = env.db.session(bind=env.db.engine)
    query = session.query(FilepathsTable.md5_hash).filter(
        FilepathsTable.md5_hash == md5_hash)
    count = query.count()
    session.close()
    if count != 0:
        msg = "This file already exists in the database."
        raise DuplicateObjectError(msg)
    return md5_hash
