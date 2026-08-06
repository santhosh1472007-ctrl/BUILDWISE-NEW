(function (window) {
    const catalog = {};
    const state = {};
    const selectedIds = {};
    const filterState = {};
    const overlayImageNodes = {};
    const selectedImageNodes = {};
    let scene = null;
    let camera = null;
    let renderer = null;
    let currentMeshes = {};
    let rotation = 0;
    let zoom = 1;
    const defaultPlaceholderImage = '/static/images/placeholder.svg';

    function normalize(value) {
        return String(value || '').toLowerCase();
    }

    function resolveImagePath(imagePath, placeholder) {
        return imagePath ? imagePath : (placeholder || defaultPlaceholderImage);
    }

    async function fetchCatalog(category) {
        try {
            const response = await fetch(`/api/hardware/${category}`);
            if (!response.ok) {
                console.warn(`Failed to fetch ${category} catalog:`, response.statusText);
                return [];
            }
            const data = await response.json();
            if (Array.isArray(data.items)) {
                catalog[category] = data.items;
            }
        } catch (error) {
            console.warn(`Error fetching ${category} catalog:`, error);
        }
        return catalog[category] || [];
    }

    async function loadCatalog(categories) {
        const fetches = categories.map((category) => {
            if (!catalog[category] || catalog[category].length === 0) {
                return fetchCatalog(category);
            }
            return Promise.resolve(catalog[category]);
        });
        await Promise.all(fetches);
    }

    function buildOptionLabel(item, category) {
        const parts = [item.name || ''];
        if (category === 'cpu' && item.socket) parts.push(`· ${item.socket}`);
        if (category === 'gpu' && item.vram_gb) parts.push(`· ${item.vram_gb}GB VRAM`);
        if (category === 'ram' && item.capacity_gb) parts.push(`· ${item.capacity_gb}GB`);
        if (category === 'motherboard' && item.form_factor) parts.push(`· ${item.form_factor}`);
        if (category === 'psu' && item.wattage) parts.push(`· ${item.wattage}W`);
        if (category === 'ssd' && item.capacity_gb) parts.push(`· ${item.capacity_gb}GB`);
        if (category === 'case' && item.form_factor) parts.push(`· ${item.form_factor}`);
        if (category === 'cooler' && item.cooler_type) parts.push(`· ${item.cooler_type}`);
        if (category === 'fan' && item.size_mm) parts.push(`· ${item.size_mm}mm`);
        return parts.filter(Boolean).join(' ');
    }

    function getSearchQuery(category) {
        const input = document.getElementById(`${category}-search`);
        return input ? normalize(input.value) : '';
    }

    function getFilteredItems(category) {
        const items = (catalog[category] || []).slice();
        const searchQuery = getSearchQuery(category);

        return items.filter((item) => {
            const brandMatch = !filterState.brand || normalize(item.brand) === normalize(filterState.brand);
            const seriesMatch = (category === 'cpu') ? (!filterState.cpu_series || normalize(item.series) === normalize(filterState.cpu_series)) :
                (category === 'gpu') ? (!filterState.gpu_series || normalize(item.series) === normalize(filterState.gpu_series)) : true;
            const socketMatch = !filterState.socket || normalize(item.socket) === normalize(filterState.socket);
            const chipsetMatch = !filterState.chipset || normalize(item.chipset) === normalize(filterState.chipset);
            const vramMatch = !filterState.vram || normalize(item.vram_gb) === normalize(filterState.vram);
            const capacityMatch = !filterState.capacity || normalize(item.capacity_gb) === normalize(filterState.capacity);
            const searchMatch = !searchQuery || normalize(item.name).includes(searchQuery) || normalize(buildOptionLabel(item, category)).includes(searchQuery);
            return brandMatch && seriesMatch && socketMatch && chipsetMatch && vramMatch && capacityMatch && searchMatch;
        });
    }

    function populateFilterOptions(config) {
        if (!config.filterMap) return;
        const filterValues = {
            brand: new Set(),
            cpu_series: new Set(),
            gpu_series: new Set(),
            socket: new Set(),
            chipset: new Set(),
            vram: new Set(),
            capacity: new Set()
        };

        (catalog.cpu || []).forEach((item) => {
            if (item.brand) filterValues.brand.add(item.brand);
            if (item.series) filterValues.cpu_series.add(item.series);
            if (item.socket) filterValues.socket.add(item.socket);
        });
        (catalog.gpu || []).forEach((item) => {
            if (item.brand) filterValues.brand.add(item.brand);
            if (item.series) filterValues.gpu_series.add(item.series);
            if (item.vram_gb) filterValues.vram.add(String(item.vram_gb));
        });
        (catalog.motherboard || []).forEach((item) => {
            if (item.brand) filterValues.brand.add(item.brand);
            if (item.chipset) filterValues.chipset.add(item.chipset);
            if (item.socket) filterValues.socket.add(item.socket);
        });
        (catalog.ram || []).forEach((item) => {
            if (item.brand) filterValues.brand.add(item.brand);
            if (item.capacity_gb) filterValues.capacity.add(String(item.capacity_gb));
        });
        ['ssd', 'psu', 'cooler', 'case', 'fan'].forEach((category) => {
            (catalog[category] || []).forEach((item) => {
                if (item.brand) filterValues.brand.add(item.brand);
            });
        });

        Object.entries(config.filterMap).forEach(([key, id]) => {
            const select = document.getElementById(id);
            if (!select) return;
            const values = Array.from(filterValues[key] || []).sort((a, b) => String(a).localeCompare(String(b)));
            const previousValue = select.value;
            select.innerHTML = '<option value="">All</option>';
            values.forEach((value) => {
                const option = document.createElement('option');
                option.value = value;
                option.textContent = value;
                select.appendChild(option);
            });
            if (filterState[key] && values.includes(filterState[key])) {
                select.value = filterState[key];
            } else if (previousValue && values.includes(previousValue)) {
                select.value = previousValue;
            }
        });
    }

    function createSelectOptions(select, category, items) {
        select.innerHTML = '';
        const selectedValue = selectedIds[category] || (items[0] ? items[0].id : '');
        if (category === 'cpu' || category === 'gpu') {
            const groups = items.reduce((acc, item) => {
                const group = item.brand || 'Other';
                if (!acc[group]) acc[group] = [];
                acc[group].push(item);
                return acc;
            }, {});
            Object.keys(groups).sort().forEach((brand) => {
                const optgroup = document.createElement('optgroup');
                optgroup.label = brand;
                groups[brand].forEach((item) => {
                    const option = document.createElement('option');
                    option.value = item.id;
                    option.textContent = item.name;
                    optgroup.appendChild(option);
                });
                select.appendChild(optgroup);
            });
        } else {
            items.forEach((item) => {
                const option = document.createElement('option');
                option.value = item.id;
                option.textContent = item.name || buildOptionLabel(item, category);
                select.appendChild(option);
            });
        }
        if (selectedValue) {
            const preserved = Array.from(select.options).find((option) => String(option.value) === String(selectedValue));
            select.value = preserved ? preserved.value : (select.options[0] ? select.options[0].value : '');
        }
    }

    function populateSelects(config) {
        if (config.filterMap) populateFilterOptions(config);
        Object.entries(config.selectorMap || {}).forEach(([category, elementId]) => {
            const select = document.getElementById(elementId);
            if (!select) return;
            const items = getFilteredItems(category);
            createSelectOptions(select, category, items);
        });
    }

    function populateSelectCategory(config, category) {
        const selectId = config.selectorMap[category];
        const select = document.getElementById(selectId);
        if (!select) return;
        const items = getFilteredItems(category);
        createSelectOptions(select, category, items);
    }

    function updateState(config) {
        Object.entries(config.selectorMap || {}).forEach(([category, elementId]) => {
            const select = document.getElementById(elementId);
            const selectedId = select ? select.value : '';
            selectedIds[category] = selectedId;
            state[category] = (catalog[category] || []).find((item) => String(item.id) === String(selectedId)) || null;
        });
    }

    function updateStateForCategory(config, category) {
        const selectId = config.selectorMap[category];
        const select = document.getElementById(selectId);
        const selectedId = select ? select.value : '';
        selectedIds[category] = selectedId;
        state[category] = (catalog[category] || []).find((item) => String(item.id) === String(selectedId)) || null;
    }

    function updateSelectedImages(config) {
        if (!config.selectedImagesContainerId) return;
        const container = document.getElementById(config.selectedImagesContainerId);
        if (!container) return;

        Object.entries(config.selectorMap || {}).forEach(([category]) => {
            const item = state[category];
            const existingCard = selectedImageNodes[category];

            if (!item) {
                if (existingCard) {
                    container.removeChild(existingCard);
                    delete selectedImageNodes[category];
                }
                return;
            }

            if (existingCard) {
                const img = existingCard.querySelector('img');
                const nameLabel = existingCard.querySelector('.component-name');
                img.src = resolveImagePath(item.image_path, config.placeholderImage);
                nameLabel.textContent = item.name;
                return;
            }

            const card = document.createElement('div');
            card.className = 'selected-image-card';
            const image = document.createElement('img');
            image.src = resolveImagePath(item.image_path, config.placeholderImage);
            image.alt = item.name;
            image.onerror = () => { image.src = resolveImagePath(null, config.placeholderImage); };
            const categoryLabel = document.createElement('div');
            categoryLabel.className = 'component-category';
            categoryLabel.textContent = category.toUpperCase();
            const nameLabel = document.createElement('div');
            nameLabel.className = 'component-name';
            nameLabel.textContent = item.name;
            card.appendChild(image);
            card.appendChild(categoryLabel);
            card.appendChild(nameLabel);
            container.appendChild(card);
            selectedImageNodes[category] = card;
        });
    }

    function updateComponentStrip(config) {
        if (!config.componentStripId) return;
        const strip = document.getElementById(config.componentStripId);
        if (!strip) return;
        strip.innerHTML = '';
        Object.keys(config.selectorMap || {}).forEach((category) => {
            const item = state[category];
            if (!item) return;
            const chip = document.createElement('div');
            chip.className = 'component-chip';
            const image = document.createElement('img');
            image.src = resolveImagePath(item.image_path, config.placeholderImage);
            image.alt = item.name;
            image.onerror = () => { image.src = resolveImagePath(null, config.placeholderImage); };
            chip.appendChild(image);
            const label = document.createElement('span');
            label.textContent = item.name;
            chip.appendChild(label);
            strip.appendChild(chip);
        });
    }

    function createOrUpdateOverlayImage(config, category, item) {
        const overlay = document.getElementById(config.overlayContainerId);
        if (!overlay) return;
        let image = overlayImageNodes[category];
        const src = resolveImagePath(item.image_path, config.placeholderImage);
        const alt = item.name || category;
        const positions = {
            cpu: { left: '24%', top: '36%' },
            cooler: { left: '24%', top: '20%' },
            motherboard: { left: '52%', top: '50%' },
            ram: { left: '61%', top: '35%' },
            ssd: { left: '74%', top: '50%' },
            psu: { left: '14%', top: '58%' },
            gpu: { left: '44%', top: '21%' },
            case: { left: '50%', top: '50%' },
            fan: { left: '80%', top: '20%' }
        }[category] || { left: '50%', top: '50%' };

        if (!image) {
            image = document.createElement('img');
            image.className = 'component-visual visible';
            image.style.position = 'absolute';
            image.style.transform = 'translate(-50%, -50%) scale(1)';
            image.onerror = () => { image.src = resolveImagePath(null, config.placeholderImage); };
            overlay.appendChild(image);
            overlayImageNodes[category] = image;
        }

        image.src = src;
        image.alt = alt;
        image.style.left = positions.left;
        image.style.top = positions.top;
        image.style.width = category === 'case' ? '260px' : '92px';
        image.style.height = category === 'case' ? '300px' : '92px';
        image.style.opacity = '0.88';
        image.style.zIndex = category === 'case' ? 1 : 2;
    }

    function updateVisualOverlay(config) {
        if (!config.overlayContainerId) return;
        const overlay = document.getElementById(config.overlayContainerId);
        if (!overlay) return;

        Object.entries(config.selectorMap || {}).forEach(([category]) => {
            const item = state[category];
            if (item) {
                createOrUpdateOverlayImage(config, category, item);
            } else if (overlayImageNodes[category]) {
                overlay.removeChild(overlayImageNodes[category]);
                delete overlayImageNodes[category];
            }
        });
    }

    function createPartMesh(category, item) {
        if (typeof THREE === 'undefined') return null;
        const sizeMap = {
            cpu: [0.42, 0.16, 0.42],
            gpu: [0.82, 0.24, 0.34],
            motherboard: [0.88, 0.06, 0.62],
            ram: [0.28, 0.12, 0.6],
            ssd: [0.22, 0.08, 0.24],
            psu: [0.44, 0.24, 0.2],
            cooler: [0.34, 0.18, 0.34],
            case: [1.3, 0.95, 0.8],
            fan: [0.24, 0.08, 0.24]
        };
        const dimensions = sizeMap[category] || [0.4, 0.2, 0.4];
        const geometry = new THREE.BoxGeometry(...dimensions);
        const material = new THREE.MeshStandardMaterial({
            color: category === 'case' ? 0x2d4b77 : 0x5ca9d9,
            roughness: 0.42,
            metalness: 0.2,
            transparent: category === 'case',
            opacity: category === 'case' ? 0.3 : 1
        });
        const mesh = new THREE.Mesh(geometry, material);
        mesh.userData = { category };
        return mesh;
    }

    function placeMeshForCategory(mesh, category) {
        if (!mesh) return;
        const positions = {
            case: [0, 0.55, 0],
            motherboard: [0, 0.16, 0],
            gpu: [0, 0.27, 0.2],
            cpu: [-0.34, 0.22, 0],
            cooler: [-0.34, 0.4, 0],
            ram: [0.34, 0.22, 0],
            ssd: [0.72, 0.16, 0],
            psu: [-0.68, 0.16, -0.02],
            fan: [0.62, 0.22, 0.34]
        };
        const [x, y, z] = positions[category] || [0, 0.2, 0];
        mesh.position.set(x, y, z);
    }

    function updatePreview(config) {
        if (!config.preview || !config.previewContainerId) return;
        const placeholder = document.getElementById(config.previewPlaceholderId || 'preview-placeholder');
        if (placeholder) placeholder.style.display = 'none';
        if (!scene) setupPreview(config);

        Object.values(currentMeshes).forEach((mesh) => {
            if (mesh) scene.remove(mesh);
        });
        currentMeshes = {};

        Object.entries(config.selectorMap || {}).forEach(([category]) => {
            const item = state[category];
            if (!item) return;
            const mesh = createPartMesh(category, item);
            placeMeshForCategory(mesh, category);
            currentMeshes[category] = mesh;
            scene.add(mesh);
        });

        if (renderer) renderer.render(scene, camera);
    }

    function setupPreview(config) {
        if (!config.preview || !config.previewContainerId || typeof THREE === 'undefined') return;
        const container = document.getElementById(config.previewContainerId);
        if (!container) return;
        container.innerHTML = '';
        const width = Math.max(container.clientWidth, 320);
        const height = Math.max(container.clientHeight, 420);

        scene = new THREE.Scene();
        scene.background = new THREE.Color(0x07131f);
        camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 1000);
        camera.position.set(0, 1.6, 4.2);
        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.setSize(width, height);
        renderer.domElement.style.width = '100%';
        renderer.domElement.style.height = '100%';
        container.appendChild(renderer.domElement);

        scene.add(new THREE.AmbientLight(0xffffff, 0.9));
        const keyLight = new THREE.DirectionalLight(0xffffff, 0.7);
        keyLight.position.set(3, 4, 4);
        scene.add(keyLight);

        const floor = new THREE.Mesh(new THREE.PlaneGeometry(6, 6), new THREE.MeshStandardMaterial({ color: 0x14253b, roughness: 0.95 }));
        floor.rotation.x = -Math.PI / 2;
        floor.position.y = 0;
        scene.add(floor);

        function animate() {
            requestAnimationFrame(animate);
            Object.values(currentMeshes).forEach((mesh) => {
                if (mesh) mesh.rotation.y = rotation + 0.03;
            });
            renderer.render(scene, camera);
        }
        animate();

        window.addEventListener('resize', () => {
            const newWidth = Math.max(container.clientWidth, 320);
            const newHeight = Math.max(container.clientHeight, 420);
            camera.aspect = newWidth / newHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(newWidth, newHeight);
        });
    }

    function applyViewCommand(action, config) {
        if (!camera) return;
        if (action === 'zoom-in') {
            zoom = Math.min(1.35, zoom + 0.1);
        } else if (action === 'zoom-out') {
            zoom = Math.max(0.7, zoom - 0.1);
        } else if (action === 'rotate-left') {
            rotation -= 0.18;
        } else if (action === 'rotate-right') {
            rotation += 0.18;
        } else if (action === 'pan') {
            camera.position.x += 0.12;
            camera.position.z = Math.max(2.2, Math.min(4.8, camera.position.z));
        } else if (action === 'reset-view') {
            zoom = 1;
            rotation = 0;
        }
        camera.position.set(0, 1.6, 4.2 * zoom);
        camera.lookAt(0, 0.25, 0);
        camera.rotation.y = rotation;
    }

    function updateSummary(config) {
        if (!config.summaryIds) return;
        const totalCost = Object.keys(config.selectorMap || {}).reduce((sum, category) => {
            const item = state[category];
            return sum + (item && item.current_price_usd ? Number(item.current_price_usd) : 0);
        }, 0);
        const powerDraw = state.psu && state.psu.wattage ? Number(state.psu.wattage) : 0;
        const performance = state.cpu && state.gpu ? 'Balanced build' : 'Select core components';

        const costNode = document.getElementById(config.summaryIds.cost);
        const perfNode = document.getElementById(config.summaryIds.performance);
        const powerNode = document.getElementById(config.summaryIds.power);
        const commentNode = document.getElementById(config.summaryIds.comment);
        if (costNode) costNode.textContent = `$${totalCost.toLocaleString()}`;
        if (perfNode) perfNode.textContent = performance;
        if (powerNode) powerNode.textContent = `${powerDraw}W`;
        if (commentNode) commentNode.textContent = state.case ? `${state.case.name} selected for the visual assembly.` : 'Select components to begin building your PC.';
    }

    async function refreshCompatibility(config) {
        if (!config.compatibilityEndpoint) return;
        const payload = {
            cpu_id: state.cpu ? state.cpu.id : null,
            gpu_id: state.gpu ? state.gpu.id : null,
            motherboard_id: state.motherboard ? state.motherboard.id : null,
            ram_id: state.ram ? state.ram.id : null,
            ssd_id: state.ssd ? state.ssd.id : null,
            psu_id: state.psu ? state.psu.id : null,
            cooler_id: state.cooler ? state.cooler.id : null,
            case_id: state.case ? state.case.id : null
        };
        const statusContainer = document.getElementById(config.compatibilityStatusId || 'compatibility-status');
        if (!statusContainer) return;
        statusContainer.innerHTML = '<div class="status-item">Checking compatibility…</div>';
        try {
            const response = await fetch(config.compatibilityEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            statusContainer.innerHTML = '';
            if (data.compatible) {
                addStatus(statusContainer, 'Compatibility', data.summary, 'ok');
            } else {
                addStatus(statusContainer, 'Compatibility', data.summary, 'error');
            }
            (data.issues || []).forEach((issue) => addStatus(statusContainer, 'Issue', issue, 'error'));
            (data.warnings || []).forEach((warning) => addStatus(statusContainer, 'Note', warning, 'warn'));
        } catch (error) {
            statusContainer.innerHTML = '';
            addStatus(statusContainer, 'Compatibility', 'Compatibility data is temporarily unavailable.', 'warn');
        }
    }

    function addStatus(container, title, message, kind) {
        const row = document.createElement('div');
        row.className = `status-item ${kind}`;
        row.innerHTML = `<span>${title}</span><strong>${message}</strong>`;
        container.appendChild(row);
    }

    async function refreshBuild(config) {
        updateState(config);
        updateVisualOverlay(config);
        updateComponentStrip(config);
        updateSelectedImages(config);
        updateSummary(config);
        if (config.preview) updatePreview(config);
        await refreshCompatibility(config);
    }

    async function refreshComponentSelection(config, category) {
        updateStateForCategory(config, category);
        updateVisualOverlay(config);
        updateComponentStrip(config);
        updateSelectedImages(config);
        updateSummary(config);
        if (config.preview) updatePreviewCategory(config, category);
        await refreshCompatibility(config);
    }

    function updatePreviewCategory(config, category) {
        if (!config.preview) return;
        if (!scene) setupPreview(config);
        if (currentMeshes[category]) {
            scene.remove(currentMeshes[category]);
            delete currentMeshes[category];
        }
        const item = state[category];
        if (!item) {
            if (renderer) renderer.render(scene, camera);
            return;
        }
        const mesh = createPartMesh(category, item);
        placeMeshForCategory(mesh, category);
        currentMeshes[category] = mesh;
        scene.add(mesh);
        if (renderer) renderer.render(scene, camera);
    }

    async function initPage(options) {
        const config = {
            categories: [],
            selectorMap: {},
            filterMap: {},
            placeholderImage: options.placeholderImage || defaultPlaceholderImage,
            selectedImagesContainerId: options.selectedImagesContainerId,
            componentStripId: options.componentStripId,
            overlayContainerId: options.overlayContainerId,
            preview: !!options.preview,
            previewContainerId: options.previewContainerId,
            previewPlaceholderId: options.previewPlaceholderId,
            compatibilityEndpoint: options.compatibilityEndpoint,
            compatibilityStatusId: options.compatibilityStatusId,
            summaryIds: options.summaryIds,
            initialCatalog: options.initialCatalog || {},
            compatibilityEnabled: !!options.compatibilityEndpoint
        };
        Object.assign(config.selectorMap, options.selectorMap || {});
        Object.assign(config.filterMap, options.filterMap || {});
        Object.assign(catalog, config.initialCatalog);
        config.categories = options.categories || Object.keys(config.selectorMap);
        Object.keys(config.filterMap).forEach((key) => {
            filterState[key] = options.initialFilterState?.[key] || '';
        });
        Object.keys(config.selectorMap).forEach((category) => {
            selectedIds[category] = '';
            state[category] = null;
        });

        await loadCatalog(config.categories);
        populateSelects(config);
        Object.keys(config.selectorMap).forEach((category) => {
            const select = document.getElementById(config.selectorMap[category]);
            if (select) {
                select.addEventListener('change', () => refreshComponentSelection(config, category));
            }
            const searchInput = document.getElementById(`${category}-search`);
            if (searchInput) {
                searchInput.addEventListener('input', () => {
                    populateSelectCategory(config, category);
                    refreshComponentSelection(config, category);
                });
            }
        });

        Object.entries(config.filterMap).forEach(([key, id]) => {
            const select = document.getElementById(id);
            if (!select) return;
            select.addEventListener('change', () => {
                filterState[key] = select.value;
                populateSelects(config);
                refreshBuild(config);
            });
        });

        if (options.previewControlsSelector) {
            document.querySelectorAll(options.previewControlsSelector).forEach((button) => {
                button.addEventListener('click', () => {
                    const action = button.getAttribute('data-action');
                    applyViewCommand(action, config);
                });
            });
        }

        if (config.preview) setupPreview(config);
        await refreshBuild(config);
    }

    async function performComponentSearch(options) {
        const categorySelect = document.getElementById(options.categorySelectId);
        const queryInput = document.getElementById(options.queryInputId);
        const resultsContainer = document.getElementById(options.resultsContainerId);
        if (!queryInput || !resultsContainer) return;
        const query = queryInput.value.trim();
        if (!query) {
            resultsContainer.innerHTML = '<p class="search-empty">Enter a search term to find components.</p>';
            return;
        }
        const category = categorySelect ? categorySelect.value : 'all';
        resultsContainer.innerHTML = '<p class="search-loading">Searching components...</p>';
        try {
            const categories = category === 'all' ? options.categories : [category];
            const responses = await Promise.all(categories.map(async (cat) => {
                const response = await fetch(`${options.searchEndpoint}?q=${encodeURIComponent(query)}&category=${encodeURIComponent(cat)}`);
                if (!response.ok) return [];
                const data = await response.json();
                const items = Array.isArray(data.items) ? data.items : [];
                return items.map((item) => ({ category: cat, ...item }));
            }));
            const items = responses.flat();
            renderSearchResults(items, resultsContainer, options.placeholderImage);
        } catch (error) {
            resultsContainer.innerHTML = '<p class="search-error">Search failed. Please try again.</p>';
            console.warn('Search error', error);
        }
    }

    function renderSearchResults(items, container, placeholderImage) {
        if (!items || items.length === 0) {
            container.innerHTML = '<p class="search-empty">No matching components found.</p>';
            return;
        }
        container.innerHTML = '';
        items.forEach((item) => {
            const card = document.createElement('div');
            card.className = 'search-result-item';
            const header = document.createElement('div');
            header.className = 'search-result-header';
            const image = document.createElement('img');
            image.src = resolveImagePath(item.image_path, placeholderImage);
            image.alt = item.name || 'Component';
            image.onerror = () => { image.src = resolveImagePath(null, placeholderImage); };
            const text = document.createElement('div');
            const title = document.createElement('h4');
            title.textContent = item.name || 'Unnamed component';
            const details = document.createElement('p');
            details.textContent = buildOptionLabel(item, item.category || '');
            text.appendChild(title);
            text.appendChild(details);
            header.appendChild(image);
            header.appendChild(text);
            card.appendChild(header);
            if (item.brand) {
                const brandLabel = document.createElement('div');
                brandLabel.className = 'search-result-meta';
                brandLabel.textContent = `Brand: ${item.brand}`;
                card.appendChild(brandLabel);
            }
            if (item.category) {
                const categoryLabel = document.createElement('div');
                categoryLabel.className = 'search-result-meta';
                categoryLabel.textContent = `Category: ${item.category}`;
                card.appendChild(categoryLabel);
            }
            container.appendChild(card);
        });
    }

    function initSearchPanel(options) {
        const config = {
            categorySelectId: options.categorySelectId,
            queryInputId: options.queryInputId,
            searchButtonId: options.searchButtonId,
            resultsContainerId: options.resultsContainerId,
            searchEndpoint: options.searchEndpoint || '/api/components/search',
            categories: options.categories || ['cpu', 'gpu', 'motherboard', 'ram', 'ssd', 'psu', 'cooler', 'case', 'fan'],
            placeholderImage: options.placeholderImage || defaultPlaceholderImage
        };
        const button = document.getElementById(config.searchButtonId);
        const queryInput = document.getElementById(config.queryInputId);
        if (button) {
            button.addEventListener('click', () => performComponentSearch(config));
        }
        if (queryInput) {
            queryInput.addEventListener('keydown', (event) => {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    performComponentSearch(config);
                }
            });
        }
    }

    window.BuildWiseBuilder = {
        initPage,
        initSearchPanel,
        fetchCatalog,
        loadCatalog,
        resolveImagePath
    };
})(window);
