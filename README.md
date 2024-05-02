# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/cfpb/sbl-filing-api/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                    |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|-------------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| src/sbl\_filing\_api/config.py                          |       52 |        0 |        8 |        1 |     98% |    14->19 |
| src/sbl\_filing\_api/entities/engine/engine.py          |       10 |        0 |        0 |        0 |    100% |           |
| src/sbl\_filing\_api/entities/models/dao.py             |       93 |        5 |        0 |        0 |     95% |40, 59, 74, 94, 121 |
| src/sbl\_filing\_api/entities/models/dto.py             |       83 |        0 |       10 |        2 |     98% |65->69, 69->73 |
| src/sbl\_filing\_api/entities/models/model\_enums.py    |       24 |        0 |        0 |        0 |    100% |           |
| src/sbl\_filing\_api/entities/repos/submission\_repo.py |      108 |        0 |       18 |        2 |     98% |61->63, 68->70 |
| src/sbl\_filing\_api/main.py                            |       41 |       11 |        2 |        0 |     74% |35-40, 44-48 |
| src/sbl\_filing\_api/routers/dependencies.py            |       17 |        0 |        8 |        2 |     92% |13->exit, 21->exit |
| src/sbl\_filing\_api/routers/filing.py                  |      155 |        0 |      120 |        0 |    100% |           |
| src/sbl\_filing\_api/services/submission\_processor.py  |       83 |        0 |       16 |        0 |    100% |           |
|                                               **TOTAL** |  **666** |   **16** |  **182** |    **7** | **97%** |           |

6 empty files skipped.


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/cfpb/sbl-filing-api/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/cfpb/sbl-filing-api/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/cfpb/sbl-filing-api/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/cfpb/sbl-filing-api/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fcfpb%2Fsbl-filing-api%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/cfpb/sbl-filing-api/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.