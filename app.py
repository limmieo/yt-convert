from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)

app.secret_key = "super_secret_key"  # Needed for flashing messages

# Dummy data for the available brands
BRANDS = {
    "thick_asian": "Thick Asian",
    "gym_baddie": "Gym Baddie",
    "polishedform": "Polished Form"
}

@app.route("/", methods=["GET", "POST"])
def index():
    # Pass available brands to the UI template
    if request.method == "POST":
        video_url = request.form.get("video_url")
        brand = request.form.get("brand")

        if not video_url or not brand:
            flash("Please enter a video URL and select a brand.")
            return redirect(url_for("index"))

        return redirect(url_for("render_video", brand=brand, video_url=video_url))

    return render_template("index.html", brands=BRANDS)


@app.route("/render/<brand>")
def render_video(brand):
    video_url = request.args.get("video_url")
    return render_template("processing.html", brand=brand, video_url=video_url)

if __name__ == "__main__":
    app.run(debug=True)
