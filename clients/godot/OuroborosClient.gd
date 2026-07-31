## Ouroboros Godot 4 client stub (Milestone 25)
## Attach to a Node; set base_url to the snapshot server.
extends Node

@export var base_url: String = "http://127.0.0.1:8765"
@export var run_id: String = ""
@export var poll_s: float = 0.5

signal frame_received(frame: Dictionary)

var _http := HTTPRequest.new()
var _t := 0.0

func _ready() -> void:
	add_child(_http)
	_http.request_completed.connect(_on_request)

func _process(delta: float) -> void:
	_t += delta
	if _t < poll_s:
		return
	_t = 0.0
	if run_id.is_empty():
		_http.request(base_url + "/runs")
	else:
		_http.request(base_url + "/runs/%s/client-stream" % run_id)

func _on_request(_result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if code != 200:
		return
	var data = JSON.parse_string(body.get_string_from_utf8())
	if typeof(data) != TYPE_DICTIONARY:
		return
	if data.has("frames") and (data["frames"] as Array).size() > 0:
		var frames: Array = data["frames"]
		frame_received.emit(frames[frames.size() - 1])
	elif data.has("runs") and run_id.is_empty():
		var runs: Array = data["runs"]
		if runs.size() > 0:
			run_id = str(runs[0].get("run_id", ""))
