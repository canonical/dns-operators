<!-- markdownlint-disable -->

<a href="../src/bind.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `bind.py`
Bind charm business logic. 



---

## <kbd>class</kbd> `BindService`
Bind service class. 




---

<a href="../src/bind.py#L86"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `prepare`

```python
prepare() → None
```

Prepare the machine. 

---

<a href="../src/bind.py#L35"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `reload`

```python
reload() → None
```

Reload the charmed-bind service. 



**Raises:**
 
 - <b>`ReloadError`</b>:  when encountering a SnapError 

---

<a href="../src/bind.py#L52"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `start`

```python
start() → None
```

Start the charmed-bind service. 



**Raises:**
 
 - <b>`StartError`</b>:  when encountering a SnapError 

---

<a href="../src/bind.py#L69"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `stop`

```python
stop() → None
```

Stop the charmed-bind service. 



**Raises:**
 
 - <b>`StopError`</b>:  when encountering a SnapError 


---

## <kbd>class</kbd> `InstallError`
Exception raised when unable to install dependencies for the service. 





---

## <kbd>class</kbd> `ReloadError`
Exception raised when unable to reload the service. 





---

## <kbd>class</kbd> `StartError`
Exception raised when unable to start the service. 





---

## <kbd>class</kbd> `StopError`
Exception raised when unable to stop the service. 





