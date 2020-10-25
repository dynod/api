# Logs service

The logs service (defined in [logs.proto](../protos/dynod_commons/api/logs.proto)) allows to configure, append and fetch logs.


---
## list

**`rpc list (Empty) returns (LoggerStatus);`**

#### *Behavior*
List known logger levels.

#### *Return*
A **`LoggerStatus`** message, including the configuration of all logger items known to the logs service.


---
## update

**`rpc update (LoggerConfig) returns (LoggerStatus);`**

#### *Behavior*
Create or update logger configuration.

#### *Input fields*
- **`name`**: the (unique) logger name to be updated; the logger will be created if it doesn't exist yet
- **`level`**: if specified (!=**`LVL_UNKNOWN`**), sets the current logger level; if the logger is created and level is unspecified, will be set to **`LVL_INFO`**

#### *Return*
On success, the logger is updated/created in logs service.

On error, possible return codes are:
- **`ERROR_PARAM_MISSING`**: there is a missing parameter in input message (**`name`**)


---
## log

**`rpc log (LogEvent) returns (LoggerStatus);`**

#### *Behavior*
Log a new line event.

#### *Input fields*
- **`logger.name`**: the logger to use to report this event
- **`logger.level`**: the level at which to report this event (**`LVL_INFO`** is unspecified)
- **`nodes`**: list of nodes impacted by this event
- **`line`**: event string to be logged

#### *Return*
On success, the event line is logged.
Note that logger will be created (with default level set to **`LVL_INFO`**) if it didn't exist yet.

On error, possible return codes are:
- **`ERROR_PARAM_MISSING`**: there is a missing parameter in input message (**`logger.name`**, **`line`**)


---
## fetch

**`rpc fetch (LogFilter) returns (stream Logs);`**

#### *Behavior*
Fetch logs for required filter (loggers + nodes combination), until stopped by the **`stop`** method.

#### *Input fields*
- **`loggers`**: list of loggers (exact match) from which to fetch logs; empty list will fetch everything
- **`nodes`**: list of regular expressions to match against node ids; empty list will fetch everything

#### *Return*
On success, streams log events (only the ones matching with the defined filters) until the **`stop`** method is called with the returned **`client_id`**.

On error, possible return codes are:
- **`ERROR_RESOURCE_UNKNOWN`**: if one of the specified logger is unknown


---
## stop

**`rpc stop (LogStop) returns (Result);`**

#### *Behavior*
Stops a running logs session, initially started by the **`fetch`** method.

#### *Input fields*
- **`client_id`**: a client ID returned by a **`fetch`** method call

#### *Return*
On success, the logs session is stopped (the logs fetching loop on **`fetch`** method stream will exit).

On error, possible return codes are:
- **`ERROR_RESOURCE_UNKNOWN`**: if the specified client ID is unknown
