@app.route("/", methods=["GET", "POST"])
def download_video():
    if request.method == "POST":
        video_url = request.form.get("url")
        print(f"Received URL: {video_url}")  # Debugging line
        if not video_url:
            return "Error: URL is required.", 400
        try:
            # Fetch the video content from the provided URL
            video_response = requests.get(video_url, stream=True)
            print(f"Video response status code: {video_response.status_code}")  # Debugging line

            if video_response.status_code == 200:
                # Extract video file name from the URL
                video_filename = video_url.split("/")[-1]
                print(f"Video filename: {video_filename}")  # Debugging line

                # Save the video to the local file system
                with open(video_filename, "wb") as video_file:
                    for chunk in video_response.iter_content(chunk_size=1024):
                        if chunk:
                            video_file.write(chunk)

                # Send the video file back to the user
                return send_file(video_filename, as_attachment=True)

            else:
                return "Error: Unable to download video.", 400

        except Exception as e:
            return f"Error: {str(e)}", 500

    return render_template_string(html_form)
