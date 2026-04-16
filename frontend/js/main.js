// frontend/js/main.js (Final Version)

// --- 【核心修正】设置Axios的全局默认配置 ---
axios.defaults.withCredentials = true;
// 为所有POST, PUT, PATCH等请求，设置默认的Content-Type
axios.defaults.headers.post['Content-Type'] = 'application/json';
axios.defaults.headers.put['Content-Type'] = 'application/json';

// --- 【核心】在文件顶部，配置Axios的全局请求拦截器 ---
axios.interceptors.request.use(
    config => {
        // 在每个请求发送之前，都检查localStorage里有没有Token
        const token = localStorage.getItem('authToken');
        if (token) {
            // 如果有，就把它加到请求的Authorization头里
            config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config;
    },
    error => {
        return Promise.reject(error);
    }
);
// 使用Vue.createApp来初始化我们的Vue应用实例
const app = Vue.createApp({

    //======================================================================
    //  1. DATA: 应用的数据核心
    //  data()函数返回一个对象，包含了应用所有需要追踪的状态。
    //  当这些数据变化时，所有使用到它们的地方都会自动更新。
    //======================================================================
    data() {
        return {
            isLoggedIn: false, // 【新增】控制用户登录状态
            username: '',      // 【新增】存放当前用户名
            // --- UI状态控制 ---
            items: [], // 【关键改动】我们现在直接使用items，不再需要rawItems
            isLoading: false,   // 控制“正在加载...”动画的显示
            showAdvancedFilters: false, // 默认关闭高级过滤器，方便调试
            showAddItemModal: false,// 控制添加商品弹窗的“开关”

            // 【新增】一个对象，用于绑定添加商品表单的数据
            newItem: {
                // 这个结构必须与我们后端API和数据库期望的字段名一致
                ItemName: '', BaseType: '', ItemCategory: '', ItemImageURL: null,
                Quality: 0, IsCorrupted: false, SkillName: null,
                ItemLevel: null, RequiredLevel: null, RequiredStr: null, RequiredDex: null, RequiredInt: null,
                PriceAmount: null, CurrencyName: 'Divine Orb', UserName: this.username,
                PhysicalDmgMin: null, PhysicalDmgMax: null,
                CritChance: null, AttacksPerSecond: null,
                // ... 其他属性...
                AllAffixes: [] // 【核心】词缀是一个数组
            },

            newAffixText: '',

            // --- 过滤器“开关”状态 ---
            // 控制每个过滤器模块是否展开
            activeFilters: {
                type: false,
                equipment: false,
                requirements: false,
                trade: false,
                stats: false,
            },

            // --- 动态选项 ---
            // 这个数组将由API在应用加载时动态填充
            availableStats: [],

            // 【核心数据模型】这是一个单一的、巨大的对象，存放着所有过滤器的当前值。
            filters: {
                // 顶部基础搜索
                search_text: '',

                // TYPE FILTERS
                item_category: 'any',
                item_rarity: 'any',
                item_level_min: null, item_level_max: null,
                quality_min: null, quality_max: null,

                // EQUIPMENT FILTERS
                damage_min: null, damage_max: null,
                aps_min: null, aps_max: null, // attacks per second
                crit_chance_min: null, crit_chance_max: null,
                dps_min: null, dps_max: null,
                phys_dps_min: null, phys_dps_max: null,
                ele_dps_min: null, ele_dps_max: null,
                reload_min: null, reload_max: null,
                armour_min: null, armour_max: null,
                evasion_min: null, evasion_max: null,
                es_min: null, es_max: null,     // energy shield
                block_min: null, block_max: null,
                spirit_min: null, spirit_max: null,
                sockets_min: null, sockets_max: null,

                // REQUIREMENTS FILTERS
                req_level_min: null, req_level_max: null,
                req_str_min: null, req_str_max: null,
                req_dex_min: null, req_dex_max: null,
                req_int_min: null, req_int_max: null,

                // TRADE FILTERS
                seller_account: '',
                collapse_listings: 'no',
                listed_time: 'any',
                sale_type: 'any',
                buyout_currency: 'any', // 默认用Any
                buyout_min: null, buyout_max: null,

                // STAT FILTERS (初始化为空数组，将由用户动态添加)
                stat_filters: []
            },
        };
    },

    //======================================================================
    //  3. METHODS: 方法
    //  这里包含了所有我们可以在HTML中通过@click等指令调用的函数。
    //======================================================================
    methods: {

        // 【新增】处理登出的逻辑
        async logout() {
            try {
                // 向后端发送登出请求
                await axios.post('http://127.0.0.1:5000/api/logout');
            } catch (error) {
                // 即使后端请求失败，前端也应该完成登出操作
                console.error("登出请求失败，但将继续在前端登出:", error);
            } finally {
                // 【核心】无论后端是否成功，都在前端清除身份信息
                localStorage.removeItem('authToken');
                localStorage.removeItem('username');
                // 跳转回登录页面
                window.location.href = 'login.html';
            }
        },

        // --- 这是一个新的辅助方法，用于检查Token是否有效 ---
        async checkLoginStatus() {
            const token = localStorage.getItem('authToken');
            if (!token) {
                window.location.href = 'login.html';
                return; // 没有Token，直接跳转
            }

            // 如果有Token，向后端验证它的有效性
            try {
                const response = await axios.get('http://127.0.0.1:5000/api/check_session');
                if (response.data.logged_in) {
                    this.isLoggedIn = true;
                    this.username = response.data.username;
                    // Token有效，加载主应用数据
                    this.initializeMainApp();
                } else {
                    // Token无效，强制登出
                    this.logout();
                }
            } catch (error) {
                // 如果API请求失败（比如后端没开，或者Token过期返回401）
                console.error("会话检查失败:", error);
                this.logout(); // 同样强制登出
            }
        },


        // --- 我们把原来的初始化逻辑，放到这个新方法里 ---
        async initializeMainApp() {
            console.log("应用初始化开始...");
            // 首先从后端加载可选的词缀列表
            try {
                const statsResponse = await axios.get('http://127.0.0.1:5000/api/stats');
                this.availableStats = statsResponse.data;
                console.log("成功加载可选词缀列表!");
            } catch (error) {
                console.error("加载可选词缀列表失败:", error);
            }
            // 然后，执行一次空的搜索来获取初始物品数据
            await this.search();
            console.log("应用初始化完成!");
        },
    
        // --- 核心搜索方法 ---
        async search() {
            this.isLoading = true;
            this.items = []; // 直接清空用于展示的items数组

            // 创建一个干净的、只包含有效值的过滤器对象发给后端
            const activeFiltersPayload = {};
            for (const key in this.filters) {
                const value = this.filters[key];
                if (value !== null && value !== undefined && value !== '' && value !== 'any') {
                    if (Array.isArray(value) && value.length === 0) continue;
                    activeFiltersPayload[key] = value;
                }
            }

            console.log("发送到后端的过滤器:", JSON.stringify(activeFiltersPayload, null, 2));

            try {
                const response = await axios.post('http://127.0.0.1:5000/api/search', activeFiltersPayload);

                // --- 【核心修正】在这里进行排序！ ---
                let fetchedItems = response.data;

                // 检查返回的是否是数组
                if (Array.isArray(fetchedItems)) {
                    // 定义货币换算比率
                    const currencyRates = {
                        'Divine Orb': 800, 'Chaos Orb': 40, 'Exalted Orb': 1, 'default': 0.05
                    };

                    // 对获取到的数据直接进行排序
                    fetchedItems.sort((a, b) => {
                        const rateA = currencyRates[a.CurrencyName] || currencyRates['default'];
                        const valueA = a.PriceAmount * rateA;
                        const rateB = currencyRates[b.CurrencyName] || currencyRates['default'];
                        const valueB = b.PriceAmount * rateB;
                        return valueA-valueB; // 升序
                    });

                    // 将排序后的结果直接赋值给this.items
                    this.items = fetchedItems;
                    console.log("成功从后端获取、排序并准备渲染数据:", this.items);
                } else {
                    console.error("后端返回的不是一个数组!", fetchedItems);
                }

            } catch (error) {
                console.error("搜索请求失败:", error);
                alert("加载数据失败！");
            } finally {
                this.isLoading = false;
            }
        },

        // --- 过滤器UI控制方法 ---
        toggleAdvancedFilters() { this.showAdvancedFilters = !this.showAdvancedFilters; },
        toggleFilterBlock(filterName) { this.activeFilters[filterName] = !this.activeFilters[filterName]; },

        // 清空所有过滤器，并重新搜索
        clearFilters() {
            // 重置filters对象为初始状态
            Object.assign(this.filters, this.defaultFilters);
            this.search(); // 重新执行搜索
        },

        // --- STAT FILTERS 的动态管理方法 ---
        handleStatInputChange(event) {
            const selectedLabel = event.target.value;
            if (!selectedLabel) return;
            const statToAdd = this.availableStats.find(stat => stat.label === selectedLabel);
            if (!statToAdd) return;

            if (!this.filters.stat_filters.some(f => f.id === statToAdd.id)) {
                this.filters.stat_filters.push({
                    id: statToAdd.id, label: statToAdd.label, active: true, min: 0, max: null
                });
            }
            event.target.value = ''; // 添加后清空输入框
        },
        removeStatFilter(index) {
            this.filters.stat_filters.splice(index, 1);
        },

        // --- 用于HTML模板的辅助方法 ---
        // 检查一个物品是否有任何专属属性，用于决定是否显示分割线
        hasProperties(item) {
            return item.Quality > 0 || item.PhysicalDmgMin || item.CritChance || item.Armour || item.BlockChance;
        },

            // 【新增】一个辅助方法，用来把后端传来的数据转换成可供前端展示的格式
         getDisplayableProperties(item) {
            const props = []; // 创建一个空数组来存放要显示的属性

            // 逐一检查每个可能的属性，如果它有值，就格式化并添加到数组里
            if (item.Quality > 0) {
                props.push({ label: 'Quality', value: `+${item.Quality}%` });
            }
            if (item.PhysicalDmgMin || item.PhysicalDmgMax) {
                props.push({ label: 'Physical Damage', value: `${item.PhysicalDmgMin}-${item.PhysicalDmgMax}` });
            }
            if (item.FireDmgMin || item.FireDmgMax) {
                props.push({ label: 'Fire Damage', value: `${item.FireDmgMin}-${item.FireDmgMax}` });
            }
            if (item.ColdDmgMin || item.ColdDmgMax) {
                props.push({ label: 'Cold Damage', value: `${item.ColdDmgMin}-${item.ColdDmgMax}` });
            }
            if (item.LightningDmgMin || item.LightningDmgMax) {
                props.push({ label: 'Lightning Damage', value: `${item.LightningDmgMin}-${item.LightningDmgMax}` });
            }
            if (item.ChaosDmgMin || item.ChaosDmgMax) {
                props.push({ label: 'Chaos Damage', value: `${item.ChaosDmgMin}-${item.ChaosDmgMax}` });
            }
            if (typeof item.CritChance === 'number') {
                props.push({ label: 'Critical Hit Chance', value: `${item.CritChance.toFixed(2)}%` });
            }
            if (typeof item.AttacksPerSecond === 'number') {
                props.push({ label: 'Attacks per Second', value: item.AttacksPerSecond.toFixed(2) });
            }
            if (typeof item.ReloadTime === 'number') {
                props.push({ label: 'ReloadTime', value: item.ReloadTime.toFixed(2) });
            }
            if (item.Spirit) {
                props.push({ label: 'Spirit', value: item.Spirit });//有问题，跟其他属性一样的格式却无法在前端显示，待进一步排查
            }
            if (typeof item.BlockChance === 'number') {
                props.push({ label: 'BlockChance', value: item.BlockChance.toFixed(2) });
            }
            if (item.Armour) {
                props.push({ label: 'Armour', value: item.Armour });
            }
            if (item.Evasion) {
                props.push({ label: 'Evasion', value: item.Evasion });
            }
            if (item.EnergyShield) {
                props.push({ label: 'EnergyShield', value: item.EnergyShield });
            }
            // ... 在这里，你可以为所有你想展示的属性添加类似的检查和格式化逻辑 ...

            return props; // 返回这个格式化好的数组
        },

        // --- 新增：打开弹窗时，重置表单 ---
        openAddItemModal() {
            // 重置newItem对象为一个干净的模板
            this.newItem = {
                ItemName: '', BaseType: '', ItemCategory: '', ItemImageURL: null,
                Quality: 0, IsCorrupted: false, SkillName: null,
                ItemLevel: null, RequiredLevel: null, RequiredStr: null, RequiredDex: null, RequiredInt: null,
                PriceAmount: null, CurrencyName: 'Divine Orb', UserName: this.username,
                AllAffixes: []
            };
            this.newAffixText = ''; // 清空临时词缀输入
            this.showAddItemModal = true; // 显示弹窗
        },

        // --- 新增：动态词缀管理方法 ---
        addNewItemAffix() {
            // 如果输入不为空，就把它添加到newItem.AllAffixes数组里
            if (this.newAffixText.trim()) {
                this.newItem.AllAffixes.push(this.newAffixText.trim());
                this.newAffixText = ''; // 清空输入框，准备下一次输入
            }
        },
        removeNewItemAffix(index) {
            // 根据索引从数组中移除一个词缀
            this.newItem.AllAffixes.splice(index, 1);
        },

        // 【新增】提交新物品的方法
        async submitNewItem() {
            try {
                // 【核心】现在发送请求时，什么都不用加！拦截器会自动处理Token。
                const response = await axios.post('http://127.0.0.1:5000/api/item', this.newItem);
                if (response.data.success) {
                    alert('Item added successfully!');
                    this.showAddItemModal = false;
                    this.search();
                }
            } catch (error) {
                if (error.response && error.response.status === 401) {
                    alert('Your session has expired. Please log in again.');
                    window.location.href = 'login.html'; // 如果token失效，跳转回登录页
                } else {
                    console.error("添加物品失败:", error);
                }
            }
        },

        async buyItem(itemId) {
            // 弹窗确认，防止用户误点
            if (!confirm(`Are you sure you want to purchase this item? (ID: ${itemId.substring(0, 8)}...)`)) {
                return;
            }

            try {
                console.log(`正在发送购买请求 for ItemID: ${itemId}`);

                // 【核心】使用axios.delete方法，并将itemId作为URL的一部分
                const response = await axios.delete(`http://127.0.0.1:5000/api/item/${itemId}`);

                if (response.data.success) {
                    alert('Purchase successful!');

                    // 【实时更新UI】从前端的items数组中，手动移除这个已购买的物品
                    const index = this.items.findIndex(item => item.ItemID === itemId);
                    if (index !== -1) {
                        this.items.splice(index, 1);
                    } else {
                        // 如果后端返回了业务逻辑上的失败（比如物品已被别人购买）
                        alert(`购买失败: ${response.data.message}`);
                    }
                }
            } catch (error) {
                console.error("购买请求失败:", error);
                // 如果是因为未授权，则跳转到登录页
                if (error.response && error.response.status === 401) {
                    alert('Your session has expired. Please log in again.');
                    window.location.href = 'login.html';
                } else {
                    alert(error.response?.data?.message || 'Failed to purchase the item.');
                }
            }
        },

        // ...
    },

    //======================================================================
    //  4. LIFECYCLE HOOKS: 生命周期钩子
    //  这些函数会在Vue实例生命周期的特定阶段自动执行。
    //================================g======================================
    created() {
        // 'created'钩子在实例被创建后立即执行，是进行初始化操作的理想位置。

        // 创建一个默认过滤器状态的深拷贝，方便一键重置
        this.defaultFilters = JSON.parse(JSON.stringify(this.filters));

    }


});

// 最后，将配置好的Vue应用，“挂载”到HTML中那个id为"app"的div上。
app.mount('#app');