const o={apiUrl:"",wsUrl:`ws://${window.location.host}`,validate(){this.apiUrl||console.warn("⚠️ API URL not configured, using default localhost:8000")}};o.validate();export{o as c};
