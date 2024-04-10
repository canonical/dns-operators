<!-- markdownlint-disable -->

<a href="../src/exceptions.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `exceptions.py`
Exceptions used by the bind charm. 



---

## <kbd>class</kbd> `BlockableError`
Exception raised when something fails and the charm should be put in a blocked state. 

Attrs:  msg (str): Explanation of the error. 

<a href="../src/exceptions.py#L14"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `__init__`

```python
__init__(msg: str)
```

Initialize a new instance of the BlockableError exception. 



**Args:**
 
 - <b>`msg`</b> (str):  Explanation of the error. 





