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

## API
### Router
`Router(workflows: List[Workflow])`

The `Router` class is defined at the root of your project, and is responsible for parsing various types of events 
and routing them through to the appropriate workflow.

#### create_lambda_handler
`Router.create_lambda_handler(decorators: List[Callable | Tuple[Callable, Dict[str, Any]]] | None)`

This method creates a function that serves as the handler/entry-point for an AWS Lambda function. You can optionally 
specify `decorators` which will ensure that the resulting function will be wrapped with the decorators of your choosing.

```python
log = Logger()

# This decorator notation is equivalent to:
# @log.inject_lambda_context(clear_state=True)
decorators = [(log.inject_lambda_context, {'clear_state': True})]

lambda_function = router.create_lambda_handler(decorators=decorators)
```

#### root_exception_handler
`Router.root_exception_handler(func: Callable)`

A root exception handler is triggered if an exception is thrown anywhere downstream and isn't caught. It is to be used 
as a last-resort catch-all exception handler.

> [!NOTE]
> The function passed to `root_exception_handler` presently is not invoked with any arguments. This is going to change 
> in the future.

```python
@router.root_exception_handler
def catch_all():
    return {'message': 'Oops I did it again'}
```

#### invoke
`Router.invoke(event: Any, context: Any = None, deps: DependencyInjector | None = None) -> Any`

This method is used to invoke the router with a given event and context. It is used for testing purposes, or is 
used when invoking a new event from within another event.

```python
router.invoke({'workflow': 'count_beans'})
```

### Workflow

The `Workflow` class defines a template for a workflow and includes a series of steps or actions to perform to complete 
a task. A workflow is defined by an event template which is expressed using a Pydantic model. The `Router` receives the 
event and checks which model it applies to, then routes it to the appropriate workflow.

> [!TIP]
> For best results, it is recommended to have a specific discriminator field in your event model using the `Literal` 
> type.

```python
from typing import Literal

from workflow_kit import Workflow
from pydantic import BaseModel


class SharpenPencils(BaseModel):
    workflow: Literal['sharpen_pencils']
    pencil_type: Literal['2B', '4B', '6B']


sharpen_pencils = Workflow(SharpenPencils)

```

#### on_init
`Workflow.on_init(func: Callable, *, decorators: List[Callable | Tuple[Callable, Dict[str, Any]]] | None = None)`

Use the `on_init` to decorate a function that will be invoked on initialisation of the workflow. This is useful for 
initialising dependencies, or performing any other setup required for the workflow.

```python
@sharpen_pencils.on_init()
def init_workflow(deps: DependencyInjector, event: SharpenPencils):
    deps.add(pencil_type=event.pencil_type)
```

#### step
`Workflow.step(func: Callable, *, decorators: List[Callable | Tuple[Callable, Dict[str, Any]]] | None = None, **kwargs)`

Use the `step` decorator to define a step in the workflow. The `step` decorator is used to decorate a function that 
will be invoked when the workflow reaches that step. Steps are executed in the order they are defined.

```python
from random import randint
from typing import Annotated

from workflow_kit import Orchestration, ResultOf


# ...rest of the Workflow definition


@sharpen_pencils.step()
def walk_to_pencil_station():
    print('Walking to pencil station')


@sharpen_pencils.step()
def move_pens_out_of_the_way():
    print('Moving the pens out of the way of the pencils')


@sharpen_pencils.step()
def unholster_sharpener():
    print('Pencil sharpener has been removed from holster')


@sharpen_pencils.step()
def commence_sharpening(pencil_type: str):
    print('Commencing pencil sharpening')
    
    if randint(1, 20) > 10:
        return f'Sharpened pencil type {pencil_type}'
    raise ValueError('Pencil snapped while attempting to sharpen')


@sharpen_pencils.step()
def send_result(orchestration: Orchestration, message: Annotated[str, ResultOf(commence_sharpening)]):
    orchestration.end({'message': message})

```

The return value of a previous step can be injected into a step on demand by adding an annotation calling the `ResultOf` 
class. The `name_or_fn` arg can either be a function name or a function itself.

> [!TIP]
> Prefer using the function itself on `ResultOf` over the name of the function. This provides a firm reference 
> so that if the function is renamed you will be aware of it as a reference error would be raised.