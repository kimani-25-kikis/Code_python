import speedtest

def test_internet_speed():
    st = speedtest.Speedtest()
    st.get_best_server()

    download = st.download() / 1_000_000
    upload = st.upload() / 1_000_000
    ping = st.results.ping

    return {
        "download_mbps": round(download, 2),
        "upload_mbps": round(upload, 2),
        "ping_ms": round(ping, 2),
    }

if __name__ == "__main__":
    results = test_internet_speed()
    for key, value in results.items():
        print(f"{key}: {value}")