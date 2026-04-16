// frontend/js/login.js

axios.defaults.headers.post['Content-Type'] = 'application/json';

const loginApp = Vue.createApp({
    data() {
        return {
            username: '',
            password: '',
            error: ''
        };
    },
    methods: {
        async login() {
            this.error = ''; // 先清空之前的错误信息
            if (!this.username || !this.password) {
                this.error = 'Please enter both username and password.';
                return;
            }

            try {
                // 向后端API发送登录请求
                const response = await axios.post('http://127.0.0.1:5000/api/login', {
                    username: this.username,
                    password: this.password
                });

                // 如果后端返回的数据表明登录成功
                if (response.data.success) {
                    // 【核心】登录成功后，把Token和用户名存到浏览器的localStorage里
                    localStorage.setItem('authToken', response.data.token);
                    localStorage.setItem('username', response.data.username);
                    // 跳转到主市集页面
                    window.location.href = 'index.html';
                }
            } catch (err) {
                // 如果请求失败（例如401 Unauthorized），显示错误信息
                if (err.response && err.response.data && err.response.data.message) {
                    this.error = err.response.data.message;
                } else {
                    this.error = 'Login failed. Please check your credentials and try again.';
                }
            }
        },

        async login() {
            // ...
            try {
                const payload = {
                    username: this.username,
                    password: this.password
                };

                const config = {
                    headers: {
                        'Content-Type': 'application/json' // 【核心修正】明确告诉后端我发的是JSON
                    },
                    withCredentials: true
                };

                // 发送请求，把payload和config作为第二和第三个参数
                const response = await axios.post('http://127.0.0.1:5000/api/login', payload, config);
                if (response.data.success) {
                    // 【核心修正】登录成功后，将Token和用户名存入浏览器的localStorage
                    localStorage.setItem('authToken', response.data.token);
                    localStorage.setItem('username', response.data.username);

                    // 然后再跳转
                    window.location.href = 'index.html';
                }
            } catch (err) { /*...*/ }
        }
    }
});

loginApp.mount('#login-app');