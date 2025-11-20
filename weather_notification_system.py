import requests
from geopy.geocoders import Nominatim
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from flask import Flask, render_template_string, jsonify, request as flask_request

app = Flask(__name__)

class WeatherNotificationSystem:
    def __init__(self, appname: str = "zafri-research-mn78s99w1"):
        self.appname = appname
        self.geolocator = Nominatim(user_agent="weather_notif_system")
        self.disaster_keywords = [
            'flood', 'flooding', 'hurricane', 'cyclone', 'typhoon', 'earthquake',
            'tsunami', 'drought', 'wildfire', 'storm', 'tornado', 'landslide',
            'avalanche', 'heatwave', 'cold wave', 'blizzard', 'volcanic eruption',
            'heavy rain', 'monsoon', 'extreme weather', 'disaster', 'emergency',
            'evacuation', 'relief', 'crisis', 'severe weather', 'tropical storm'
        ]
        
    def get_country_from_coordinates(self, latitude: float, longitude: float) -> str:
        try:
            location = self.geolocator.reverse(f"{latitude}, {longitude}", language='en')
            if location and 'address' in location.raw:
                country = location.raw['address'].get('country', '')
                print(f"🌍 Country: {country}")
                return country
        except Exception as e:
            print(f"❌ Geolocation error: {e}")
        return None
    
    def fetch_reliefweb_reports(self, country: str, limit: int = 100):
        try:
            print(f"🔍 Fetching reports for: {country}")
            
            base_url = "https://api.reliefweb.int/v2/reports"
            query_string = f"appname={self.appname}&query[fields][]=country&query[value]={country}&limit={limit}"
            full_url = f"{base_url}?{query_string}"
            
            print(f"📤 URL: {full_url}")
            
            response = requests.get(full_url, timeout=30)
            print(f"📥 Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                total_count = data.get('totalCount', 0)
                reports = data.get('data', [])
                print(f"✅ Found {len(reports)} reports (total: {total_count})")
                return reports
            else:
                print(f"❌ Error: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            return []
    
    def is_disaster_report(self, text: str) -> tuple:
        if not text:
            return False, 0.0, []
        
        text_lower = text.lower()
        matched_keywords = [kw for kw in self.disaster_keywords if kw in text_lower]
        
        try:
            corpus = [' '.join(self.disaster_keywords), text_lower]
            vectorizer = TfidfVectorizer(stop_words='english', max_features=100)
            tfidf_matrix = vectorizer.fit_transform(corpus)
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        except:
            similarity = 0.0
        
        keyword_score = len(matched_keywords) / len(self.disaster_keywords)
        final_score = (similarity * 0.6) + (keyword_score * 0.4)
        is_disaster = final_score >= 0.08 or len(matched_keywords) >= 1
        
        return is_disaster, round(final_score, 3), matched_keywords
    
    def process_all_reports(self, reports):
        all_reports = []
        disaster_reports = []
        
        for report in reports:
            fields = report.get('fields', {})
            title = fields.get('title', '')
            body = fields.get('body', '')
            
            is_disaster, score, keywords = self.is_disaster_report(f"{title} {body}")
            
            disaster_info = fields.get('disaster', [])
            disaster_type_info = fields.get('disaster_type', [])
            has_disaster_tag = len(disaster_info) > 0 or len(disaster_type_info) > 0
            
            primary_country = fields.get('primary_country', {})
            country_name = primary_country.get('name', '') if primary_country else ''
            
            date_info = fields.get('date', {})
            date_str = date_info.get('created', 'N/A')
            
            report_data = {
                'title': title,
                'date': date_str,
                'country': country_name,
                'disaster_types': [dt.get('name', '') for dt in disaster_type_info],
                'url': fields.get('url', ''),
                'score': score,
                'keywords': keywords[:5],
                'has_disaster_tag': has_disaster_tag
            }
            
            all_reports.append(report_data)
            if is_disaster or has_disaster_tag:
                disaster_reports.append(report_data)
        
        return all_reports, sorted(disaster_reports, key=lambda x: x['score'], reverse=True)
    
    def process_location(self, latitude: float, longitude: float):
        print(f"\n🎯 Processing: ({latitude}, {longitude})")
        
        country = self.get_country_from_coordinates(latitude, longitude)
        if not country:
            return {'error': 'Could not determine country'}
        
        reports = self.fetch_reliefweb_reports(country)
        all_reports, disaster_reports = self.process_all_reports(reports)
        
        print(f"📊 Result: {len(disaster_reports)} disasters / {len(reports)} total\n")
        
        return {
            'country': country,
            'total_fetched': len(reports),
            'disasters_found': len(disaster_reports),
            'all_reports': all_reports,
            'disaster_reports': disaster_reports
        }

weather_system = WeatherNotificationSystem()

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Disaster Alert System</title>
    <style>
        body { font-family: Arial; max-width: 1200px; margin: 50px auto; padding: 20px; }
        input { padding: 10px; margin: 5px; width: 200px; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
        .stats { display: flex; gap: 20px; margin: 20px 0; }
        .stat { background: #f0f0f0; padding: 20px; border-radius: 5px; text-align: center; }
        .report { border: 1px solid #ddd; padding: 15px; margin: 10px 0; }
        .disaster { background: #fff3cd; border-left: 4px solid #ff9800; }
    </style>
</head>
<body>
    <h1>🌍 Disaster Alert System</h1>
    
    <div>
        <input type="number" id="lat" placeholder="Latitude" value="23.8103">
        <input type="number" id="lon" placeholder="Longitude" value="90.4125">
        <button onclick="check()">Check Disasters</button>
    </div>
    
    <div id="results"></div>
    
    <script>
        async function check() {
            const lat = document.getElementById('lat').value;
            const lon = document.getElementById('lon').value;
            
            document.getElementById('results').innerHTML = '<p>Loading...</p>';
            
            try {
                const res = await fetch('/api/check', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({latitude: parseFloat(lat), longitude: parseFloat(lon)})
                });
                
                const data = await res.json();
                
                if (data.error) {
                    document.getElementById('results').innerHTML = '<p>Error: ' + data.error + '</p>';
                    return;
                }
                
                let html = '<h2>Summary for ' + data.country + '</h2>';
                html += '<div class="stats">';
                html += '<div class="stat"><h3>' + data.disasters_found + '</h3><p>Disasters</p></div>';
                html += '<div class="stat"><h3>' + data.total_fetched + '</h3><p>Total Reports</p></div>';
                html += '</div>';
                
                html += '<h3>🚨 Disaster Reports (' + data.disasters_found + ')</h3>';
                if (data.disaster_reports.length === 0) {
                    html += '<p>No disasters detected</p>';
                } else {
                    data.disaster_reports.forEach(r => {
                        html += '<div class="report disaster">';
                        html += '<h4>' + r.title + '</h4>';
                        html += '<p>📅 ' + new Date(r.date).toLocaleDateString() + ' | 📍 ' + r.country + '</p>';
                        if (r.disaster_types.length > 0) {
                            html += '<p>Type: ' + r.disaster_types.join(', ') + '</p>';
                        }
                        if (r.url) html += '<a href="' + r.url + '" target="_blank">View Report</a>';
                        html += '</div>';
                    });
                }
                
                html += '<h3>📋 All Reports (' + data.total_fetched + ')</h3>';
                data.all_reports.forEach(r => {
                    html += '<div class="report">';
                    html += '<h4>' + r.title + '</h4>';
                    html += '<p>📅 ' + new Date(r.date).toLocaleDateString() + '</p>';
                    html += '</div>';
                });
                
                document.getElementById('results').innerHTML = html;
            } catch(error) {
                document.getElementById('results').innerHTML = '<p>Error: ' + error.message + '</p>';
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/api/check', methods=['POST'])
def check_disasters():
    try:
        data = flask_request.json
        result = weather_system.process_location(data['latitude'], data['longitude'])
        return jsonify(result)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Server running at: http://localhost:5000")
    app.run(debug=True, port=5000)