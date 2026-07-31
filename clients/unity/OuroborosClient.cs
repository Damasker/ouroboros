// Ouroboros Unity client stub (Milestone 25)
// Drop into a GameObject; requires Unity 2022+ with UnityWebRequest.
using System;
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

[Serializable]
public class OuroborosFrame
{
    public string protocol;
    public string version;
    public string run_id;
    public float time;
}

public class OuroborosClient : MonoBehaviour
{
    public string baseUrl = "http://127.0.0.1:8765";
    public string runId = "";
    public float pollSeconds = 0.5f;

    public event Action<string> OnRawFrameJson;

    void Start() => StartCoroutine(PollLoop());

    IEnumerator PollLoop()
    {
        while (true)
        {
            string url = string.IsNullOrEmpty(runId)
                ? $"{baseUrl}/runs"
                : $"{baseUrl}/runs/{runId}/client-stream";
            using var req = UnityWebRequest.Get(url);
            yield return req.SendWebRequest();
            if (req.result == UnityWebRequest.Result.Success)
                OnRawFrameJson?.Invoke(req.downloadHandler.text);
            yield return new WaitForSeconds(pollSeconds);
        }
    }
}
