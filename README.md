# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/cfpb/sbl-filing-api/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|-------------------------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| src/sbl\_filing\_api/config.py                                      |       57 |        2 |        2 |        1 |     95% |     15-16 |
| src/sbl\_filing\_api/entities/engine/engine.py                      |       11 |        0 |        0 |        0 |    100% |           |
| src/sbl\_filing\_api/entities/models/dao.py                         |       90 |        5 |        0 |        0 |     94% |44, 63, 78, 99, 130 |
| src/sbl\_filing\_api/entities/models/dto.py                         |       71 |        0 |        8 |        2 |     97% |73->77, 77->81 |
| src/sbl\_filing\_api/entities/models/model\_enums.py                |       24 |        0 |        0 |        0 |    100% |           |
| src/sbl\_filing\_api/entities/repos/submission\_repo.py             |      118 |       13 |       16 |        0 |     89% |87, 121-124, 150-158 |
| src/sbl\_filing\_api/main.py                                        |       41 |       11 |        0 |        0 |     73% |35-40, 44-48 |
| src/sbl\_filing\_api/routers/filing.py                              |      194 |        1 |       30 |        1 |     99% |       410 |
| src/sbl\_filing\_api/services/file\_handler.py                      |       22 |        0 |        4 |        0 |    100% |           |
| src/sbl\_filing\_api/services/multithread\_handler.py               |       27 |        2 |        0 |        0 |     93% |     18-19 |
| src/sbl\_filing\_api/services/request\_action\_validator.py         |       64 |        3 |       16 |        0 |     96% | 42, 55-56 |
| src/sbl\_filing\_api/services/request\_handler.py                   |       14 |        0 |        2 |        0 |    100% |           |
| src/sbl\_filing\_api/services/submission\_processor.py              |       85 |        1 |       18 |        2 |     97% |64, 96->99 |
| src/sbl\_filing\_api/services/validators/base\_validator.py         |       17 |        0 |        6 |        0 |    100% |           |
| src/sbl\_filing\_api/services/validators/filing\_validators.py      |       28 |        0 |        8 |        0 |    100% |           |
| src/sbl\_filing\_api/services/validators/institution\_validators.py |       22 |        0 |        4 |        0 |    100% |           |
| src/sbl\_filing\_api/services/validators/period\_validators.py      |       10 |        0 |        2 |        0 |    100% |           |
| src/sbl\_filing\_api/services/validators/submission\_validators.py  |       16 |        0 |        4 |        0 |    100% |           |
|                                                           **TOTAL** |  **911** |   **38** |  **120** |    **6** | **96%** |           |

7 empty files skipped.


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