<!-- markdownlint-disable -->

<a href="../src/bind.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `bind.py`
Bind charm business logic. 



---

## <kbd>class</kbd> `BindService`
Bind service class. 




---

<a href="../src/bind.py#L77"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `install_snap_package`

```python
install_snap_package(
    snap_name: str,
    snap_channel: str,
    refresh: bool = False
) → None
```

Installs snap package. 



**Args:**
 
 - <b>`snap_name`</b>:  the snap package to install 
 - <b>`snap_channel`</b>:  the snap package channel 
 - <b>`refresh`</b>:  whether to refresh the snap if it's already present. 



**Raises:**
 
 - <b>`BlockableError`</b>:  when encountering a SnapError or a SnapNotFoundError 

---

<a href="../src/bind.py#L70"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `prepare`

```python
prepare() → None
```

Prepare the machine. 

---

<a href="../src/bind.py#L19"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `reload`

```python
reload() → None
```

Reload the charmed-bind service. 



**Raises:**
 
 - <b>`BlockableError`</b>:  when encountering a SnapError 

---

<a href="../src/bind.py#L36"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `start`

```python
start() → None
```

Start the charmed-bind service. 



**Raises:**
 
 - <b>`BlockableError`</b>:  when encountering a SnapError 

---

<a href="../src/bind.py#L53"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `stop`

```python
stop() → None
```

Stop the charmed-bind service. 



**Raises:**
 
 - <b>`BlockableError`</b>:  when encountering a SnapError 


