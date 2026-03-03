document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const toolModal = document.getElementById('toolModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalDesc = document.getElementById('modalDesc');
    const closeBtn = document.querySelector('.close-btn');
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const fileList = document.getElementById('fileList');
    const processBtn = document.getElementById('processBtn');
    const optionsArea = document.getElementById('optionsArea');
    const fileListHeader = document.getElementById('fileListHeader');

    let currentTool = '';
    let selectedFiles = [];

    window.clearFiles = () => {
        selectedFiles = [];
        fileList.innerHTML = '';
        fileListHeader.style.display = 'none';
        processBtn.style.display = 'none';
    };

    const toolMeta = {
        'merge': { title: 'Merge PDF', desc: 'Combine multiple files into one PDF sequentially.' },
        'split': { title: 'Split PDF', desc: 'Extract pages or ranges. Range format: 1-5, 8, 11-13', options: [['range', 'Page Range (e.g. 1-5)', 'text', '1-5']] },
        'compress': { title: 'Compress PDF', desc: 'Shrink file size while optimized for screen quality.' },
        'protect': { title: 'Protect PDF', desc: 'Encrypt your file with a password.', options: [['password', 'Password', 'password', '']] },
        'unlock': { title: 'Unlock PDF', desc: 'Remove password/security. (Required for encrypted files)', options: [['password', 'Current Password', 'password', '']] },
        'rotate': { title: 'Rotate PDF', desc: 'Flip pages 90/180/270 degrees.', options: [['angle', 'Rotation Angle', 'number', '90']] },
        'delete': { title: 'Delete Pages', desc: 'Remove specific pages from the doc.', options: [['pages', 'Pages to Remove (e.g. 1, 3, 5-7)', 'text', '1']] },
        'watermark': { title: 'Watermark', desc: 'Add a text watermark to every page.', options: [['text', 'Watermark Text', 'text', 'CONFIDENTIAL']] },
        'reorder': { title: 'Reorder Pages', desc: 'Change page sequence. Example: 3, 1, 2, 4', options: [['order', 'New Page Order', 'text', '1, 2, 3']] },
        'img2pdf': { title: 'Image to PDF', desc: 'Convert multiple images into a single PDF.', accept: 'image/*' },
        'pdf2img': { title: 'PDF to Image', desc: 'Extract pages as JPEG images.' },
        'txt2pdf': { title: 'Text to PDF', desc: 'Convert plain text into a PDF file.', accept: '.txt' },
        'grayscale': { title: 'Grayscale', desc: 'Convert all colors in the document to black and white.' },
        'extract_text': { title: 'Extract Text', desc: 'Retrieve all text from the PDF into a clean .txt file.' },
        'repair': { title: 'Repair PDF', desc: 'Recover content from slightly damaged or unreadable PDFs.' },
        'pagenum': { title: 'Add Page Numbers', desc: 'Add sequentially numbered labels to the footer.', options: [['start', 'Start Number', 'number', '1'], ['position', 'Position (bottom-right/center/left)', 'text', 'center']] },
        'invert': { title: 'Invert Colors', desc: 'Flip all document colors (Negative effect). Great for dark mode reading.' },
        'flatten': { title: 'Flatten PDF', desc: 'Remove interactive elements and lock the content layers.' },
        'crop': { title: 'Crop PDF', desc: 'Remove margins from all pages.', options: [['margin', 'Margin to remove (%)', 'number', '10']] },
        'pdf2word': { title: 'PDF to Word', desc: 'Convert document into an editable .docx file.' },
        'resize': { title: 'Resize PDF', desc: 'Scale pages to a specific standard size.', options: [['size', 'Target Size (A4, Letter, Legal)', 'text', 'A4']] },
        'header': { title: 'Add Header', desc: 'Add text labels to the top of the document.', options: [['text', 'Header Text', 'text', 'DRAFT']] },
        'extract_img': { title: 'Extract Images', desc: 'Extract all embedded raw images into a ZIP file.' },
        'remove_blank': { title: 'Remove Blank Pages', desc: 'Automatically scan and remove completely empty document pages.' },
        'redact': { title: 'Redact Text', desc: 'Search and permanently black out a specific word throughout the document.', options: [['text', 'Word to Redact', 'text', 'Confidential']] },
        'remove_annots': { title: 'Strip Annotations', desc: 'Delete all comments, highlights, forms, and notes from the PDF.' }
    };

    // Tool Opening
    window.openTool = (tool) => {
        const info = toolMeta[tool];
        if (!info) return;

        currentTool = tool;
        selectedFiles = [];
        fileList.innerHTML = '';
        processBtn.style.display = 'none';
        processBtn.innerHTML = '<span>⚡ PROCESS NOW</span>';
        processBtn.disabled = false;
        fileInput.accept = info.accept || 'application/pdf';

        modalTitle.innerText = info.title;
        modalDesc.innerText = info.desc;

        // Reset and inject options
        optionsArea.innerHTML = '';
        if (info.options) {
            info.options.forEach(([id, name, type, def]) => {
                const group = document.createElement('div');
                group.className = 'option-group';
                group.innerHTML = `<label>${name}</label><input type="${type}" id="opt_${id}" class="option-input" value="${def}">`;
                optionsArea.appendChild(group);
            });
            optionsArea.style.display = 'flex';
        } else {
            optionsArea.style.display = 'none';
        }

        toolModal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    };

    closeBtn.addEventListener('click', () => {
        toolModal.style.display = 'none';
        document.body.style.overflow = 'auto';
    });

    uploadArea.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        const files = Array.from(e.target.files);
        addFiles(files);
    });

    function addFiles(files) {
        files.forEach(file => {
            selectedFiles.push(file);
            const item = document.createElement('div');
            item.className = 'file-item';
            item.innerHTML = `<span class="file-name" title="${file.name}">${file.name}</span> <span class="file-size">${(file.size / 1024 / 1024).toFixed(2)} MB</span>`;
            fileList.appendChild(item);
        });

        if (selectedFiles.length > 0) {
            fileListHeader.style.display = 'flex';
            processBtn.style.display = 'flex';
        }
    }

    processBtn.addEventListener('click', async () => {
        processBtn.disabled = true;
        processBtn.innerHTML = '<span>⏳ INJECTING TOXINS...</span>';

        const formData = new FormData();
        selectedFiles.forEach(file => formData.append('files', file));
        formData.append('tool', currentTool);

        // Append options
        if (toolMeta[currentTool].options) {
            toolMeta[currentTool].options.forEach(([id]) => {
                formData.append(id, document.getElementById(`opt_${id}`).value);
            });
        }

        try {
            const res = await fetch('/process-pdf', {
                method: 'POST',
                body: formData
            });

            if (res.ok) {
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                let ext = 'pdf';
                if (currentTool === 'pdf2img' || currentTool === 'extract_img') ext = 'zip';
                else if (currentTool === 'pdf2word') ext = 'docx';
                else if (currentTool === 'extract_text') ext = 'txt';

                a.download = `toxic_${currentTool}_output.${ext}`;
                document.body.appendChild(a);
                a.click();
                a.remove();

                processBtn.innerHTML = '<span>✅ SUCCESSFUL</span>';
                setTimeout(() => {
                    toolModal.style.display = 'none';
                    document.body.style.overflow = 'auto';
                    processBtn.disabled = false;
                }, 1000);
            } else {
                const err = await res.text();
                alert('Fatal Error: ' + err);
                processBtn.disabled = false;
                processBtn.innerHTML = '<span>⚡ PROCESS NOW</span>';
            }
        } catch (error) {
            alert('Connection Lost.');
            processBtn.disabled = false;
            processBtn.innerHTML = '<span>⚡ PROCESS NOW</span>';
        }
    });

    // Theme Toggle Logic
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = themeToggle.querySelector('i');

    // Check saved preference
    if (localStorage.getItem('theme') === 'light') {
        document.body.classList.add('light-mode');
        themeIcon.classList.replace('fa-moon', 'fa-sun');
    }

    themeToggle.addEventListener('click', () => {
        document.body.classList.toggle('light-mode');
        const isLight = document.body.classList.contains('light-mode');

        // Update Icon
        if (isLight) {
            themeIcon.classList.replace('fa-moon', 'fa-sun');
            localStorage.setItem('theme', 'light');
        } else {
            themeIcon.classList.replace('fa-sun', 'fa-moon');
            localStorage.setItem('theme', 'dark');
        }
    });
});
