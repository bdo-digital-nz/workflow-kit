# WorkflowKit
This library provides a lightweight framework for building event-driven (AWS Lambda–style) 
applications with clear routing, workflow orchestration, and dependency injection, centered 
around Pydantic models for event validation.

## Installation
```console
pip install workflow-kit
```

## Basic Usage
There are two primary interfaces in this library which are used together to design workflows, 
`Router` and `Workflow`. The basic anatomy is a `Router` is defined at the project root and 
is used to create an appropriate AWS Lambda handler function, which parses the event into a
Pydantic model, and then routes it to the applicable `Workflow`.

The `Workflow` is in essence a template, or a sequence of events to complete the action.

```python
# router.py

from workflow_kit import Router

from .workflows import create_user, process_payment

router = Router([create_user, process_payment])

# Now we define the Lambda handler using `router`
lambda_function = router.create_lambda_handler()
```

```python
# create_user.py

from typing import Literal

from pydantic import BaseModel
from workflow_kit import Workflow, DependencyInjector


class CreateUser(BaseModel):
    type: Literal['create_user']
    name: str
    email: str
    active: bool


create_user = Workflow(CreateUser)


@create_user.on_init()
def init_workflow(deps: DependencyInjector):
    db = DB()
    config = {'name_unique': True}

    # Read below on `DependencyInjector` usage
    deps.add(db, config=config)


@create_user.step()
def check_name_is_unique(db: DB, data: CreateUser):
    ...
    # Implement logic


@create_user.step()
def create_user(db: DB, data: CreateUser):
    table = db.table('users')
    return table.create({'name': data.name, 'email': data.email, 'active': data.active})

```
