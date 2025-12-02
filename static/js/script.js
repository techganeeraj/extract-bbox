// File input element
const fileInput = document.getElementById('fileInput');
const uploadBox = document.getElementById('uploadBox');
const fileInfo = document.getElementById('fileInfo');
const submitBtn = document.getElementById('submitBtn');
const resultsSection = document.getElementById('resultsSection');
const resultsContainer = document.getElementById('resultsContainer');
const errorMessage = document.getElementById('errorMessage');
const pdfViewerSection = document.getElementById('pdfViewerSection');
const pdfCanvas = document.getElementById('pdfCanvas');
const pdfCanvasWrapper = document.getElementById('pdfCanvasWrapper');
const bboxOverlay = document.getElementById('bboxOverlay');
const closePdfBtn = document.getElementById('closePdfBtn');

let pdfDoc = null;
let pdfPage = null;
let boundingBoxes = []; // Array of arrays, each containing bounding boxes for a line item
let selectedLineItems = new Set(); // Track which line items are selected

// Tag label mappings for better display
const tagLabels = {
    'claimId': 'Claim ID',
    'lineId': 'Line ID',
    'serviceDateTime': 'Service Date/Time',
    'itemCode': 'Item Code',
    'dataSource': 'Data Source',
    'lineTypeSectionTotalItem': 'Line Type',
    'sectionHeaderLineSectionType': 'Section Header/Type',
    'billsParticularsCostCenters': 'Item Description',
    'qty': 'Quantity',
    'price': 'Price',
    'discount': 'Discount',
    'discountPercent': 'Discount Percent',
    'paidByPatientHospitalBill': 'Paid by Patient/Hospital Bill',
    'philhealthHospBillPortionAmount': 'PhilHealth Hospital Bill Portion',
    'billsParticularsCostCenterAmount': 'Bill Particulars Amount'
};

// Initialize event listeners
fileInput.addEventListener('change', handleFileSelect);
uploadBox.addEventListener('dragover', handleDragOver);
uploadBox.addEventListener('dragleave', handleDragLeave);
uploadBox.addEventListener('drop', handleDrop);
submitBtn.addEventListener('click', handleSubmit);
closePdfBtn.addEventListener('click', closePdfViewer);

let selectedFile = null;
let pdfBlobUrl = null;

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        processFile(file);
    }
}

function handleDragOver(e) {
    e.preventDefault();
    uploadBox.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    uploadBox.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    uploadBox.classList.remove('dragover');
    
    const file = e.dataTransfer.files[0];
    if (file && file.type === 'application/pdf') {
        processFile(file);
        fileInput.files = e.dataTransfer.files;
    } else {
        showError('Please upload a valid PDF file.');
    }
}

function processFile(file) {
    if (file.type !== 'application/pdf') {
        showError('Please upload a valid PDF file.');
        return;
    }
    
    selectedFile = file;
    fileInfo.textContent = `Selected: ${file.name} (${formatFileSize(file.size)})`;
    fileInfo.classList.add('show');
    submitBtn.disabled = false;
    hideError();
    
    // Display PDF in viewer
    displayPdf(file);
}

async function displayPdf(file) {
    // Clean up previous blob URL if exists
    if (pdfBlobUrl) {
        URL.revokeObjectURL(pdfBlobUrl);
    }
    
    // Create blob URL for the PDF
    pdfBlobUrl = URL.createObjectURL(file);
    
    try {
        // Set up PDF.js worker
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        
        // Load PDF
        const loadingTask = pdfjsLib.getDocument({ url: pdfBlobUrl });
        pdfDoc = await loadingTask.promise;
        
        // Render first page
        await renderPdfPage(1);
        
        pdfViewerSection.style.display = 'flex';
    } catch (error) {
        console.error('Error loading PDF:', error);
        showError('Failed to load PDF for preview.');
    }
}

async function renderPdfPage(pageNum) {
    if (!pdfDoc) return;
    
    try {
        pdfPage = await pdfDoc.getPage(pageNum);
        
        // Render PDF at 100% scale (actual size)
        const scale = 1.0;
        const viewport = pdfPage.getViewport({ scale: scale });
        
        // Set canvas dimensions to actual PDF size
        pdfCanvas.height = viewport.height;
        pdfCanvas.width = viewport.width;
        
        // Set canvas CSS dimensions to match rendered dimensions
        pdfCanvas.style.width = `${viewport.width}px`;
        pdfCanvas.style.height = `${viewport.height}px`;
        
        // Get context and clear canvas
        const ctx = pdfCanvas.getContext('2d');
        ctx.clearRect(0, 0, pdfCanvas.width, pdfCanvas.height);
        
        // Render PDF page
        const renderContext = {
            canvasContext: ctx,
            viewport: viewport
        };
        
        await pdfPage.render(renderContext).promise;
        
        // Draw bounding boxes if available
        if (boundingBoxes.length > 0 && selectedLineItems.size > 0) {
            drawBoundingBoxes(viewport);
        }
    } catch (error) {
        console.error('Error rendering PDF page:', error);
    }
}

function drawBoundingBoxes(viewport) {
    const ctx = pdfCanvas.getContext('2d');
    const colors = ['#00d4ff', '#5b9bd5', '#7b68ee', '#9b8aff', '#ff6b6b', '#4ecdc4', '#ffe66d', '#ff6b9d'];
    
    // Only draw bounding boxes for selected line items
    selectedLineItems.forEach(lineItemIndex => {
        if (!boundingBoxes[lineItemIndex]) return;
        
        const lineItemBboxes = boundingBoxes[lineItemIndex];
        const color = colors[lineItemIndex % colors.length];
        
        lineItemBboxes.forEach(bbox => {
            if (!bbox || !bbox.bbox || bbox.bbox.length !== 4) return;
            
            const [y_min, x_min, y_max, x_max] = bbox.bbox;
            
            // Skip empty bounding boxes
            if (y_min === 0 && x_min === 0 && y_max === 0 && x_max === 0) return;
            
            // Scale normalized coordinates (0-1000) to canvas dimensions
            const abs_y_min = Math.round((y_min / 1000) * viewport.height);
            const abs_x_min = Math.round((x_min / 1000) * viewport.width);
            const abs_y_max = Math.round((y_max / 1000) * viewport.height);
            const abs_x_max = Math.round((x_max / 1000) * viewport.width);
            
            // Draw rectangle
            ctx.strokeStyle = color;
            ctx.lineWidth = 2;
            ctx.strokeRect(abs_x_min, abs_y_min, abs_x_max - abs_x_min, abs_y_max - abs_y_min);
            
            // No labels for cleaner display
        });
    });
}

function toggleLineItemBoundingBoxes(lineItemIndex, isChecked) {
    if (isChecked) {
        selectedLineItems.add(lineItemIndex);
    } else {
        selectedLineItems.delete(lineItemIndex);
    }
    
    // Redraw PDF with updated bounding boxes
    if (pdfDoc && pdfPage) {
        renderPdfPage(1);
    }
}

function closePdfViewer() {
    pdfViewerSection.style.display = 'none';
    if (pdfBlobUrl) {
        URL.revokeObjectURL(pdfBlobUrl);
        pdfBlobUrl = null;
    }
    pdfDoc = null;
    pdfPage = null;
    boundingBoxes = [];
    if (pdfCanvas) {
        const ctx = pdfCanvas.getContext('2d');
        ctx.clearRect(0, 0, pdfCanvas.width, pdfCanvas.height);
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function handleSubmit() {
    if (!selectedFile) {
        showError('Please select a PDF file first.');
        return;
    }
    
    // Show loading state
    submitBtn.classList.add('loading');
    submitBtn.disabled = true;
    hideError();
    resultsSection.style.display = 'none';
    
    // Create form data
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    // Send request
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'An error occurred while processing the file.');
            });
        }
        return response.json();
    })
    .then(data => {
        displayResults(data);
        submitBtn.classList.remove('loading');
        submitBtn.disabled = false;
    })
    .catch(error => {
        showError(error.message || 'Failed to process the PDF file. Please try again.');
        submitBtn.classList.remove('loading');
        submitBtn.disabled = false;
    });
}

function displayResults(data) {
    resultsContainer.innerHTML = '';
    boundingBoxes = [];
    selectedLineItems.clear();
    
    if (!data.line_details1 || !Array.isArray(data.line_details1) || data.line_details1.length === 0) {
        resultsContainer.innerHTML = '<p style="text-align: center; color: #a0a0a0; padding: 40px;">No line items found in the document.</p>';
        resultsSection.style.display = 'block';
        return;
    }
    
    // Collect bounding boxes per line item
    data.line_details1.forEach((item, index) => {
        const lineItemBboxes = [];
        
        // Extract bounding boxes from item
        Object.keys(tagLabels).forEach(key => {
            if (item[key] && typeof item[key] === 'object') {
                const field = item[key];
                // Add label bounding box
                if (field.labelBbox && Array.isArray(field.labelBbox) && field.labelBbox.length === 4) {
                    lineItemBboxes.push({
                        bbox: field.labelBbox,
                        label: tagLabels[key] + ' (Label)',
                        type: 'label',
                        fieldKey: key
                    });
                }
                // Add value bounding box
                if (field.valueBbox && Array.isArray(field.valueBbox) && field.valueBbox.length === 4) {
                    lineItemBboxes.push({
                        bbox: field.valueBbox,
                        label: tagLabels[key] + (field.value ? `: ${field.value}` : ''),
                        type: 'value',
                        fieldKey: key
                    });
                }
            }
        });
        
        boundingBoxes.push(lineItemBboxes);
        
        // Create line item element with checkbox
        const lineItemDiv = createLineItemElement(item, index + 1, index);
        resultsContainer.appendChild(lineItemDiv);
    });
    
    // Redraw PDF with bounding boxes if PDF is already loaded
    if (pdfDoc) {
        renderPdfPage(1);
    }
    
    resultsSection.style.display = 'block';
}

// Add resize event listener to re-render PDF on window resize
let resizeTimeout;
window.addEventListener('resize', () => {
    // Debounce resize events to avoid excessive re-renders
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        if (pdfDoc) {
            renderPdfPage(1);
        }
    }, 250);
});

function createLineItemElement(item, index, lineItemIndex) {
    const lineItemDiv = document.createElement('div');
    lineItemDiv.className = 'line-item';
    
    // Header
    const headerDiv = document.createElement('div');
    headerDiv.className = 'line-item-header';
    
    // Checkbox for toggling bounding boxes
    const checkboxWrapper = document.createElement('div');
    checkboxWrapper.className = 'line-item-checkbox-wrapper';
    
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.id = `line-item-checkbox-${lineItemIndex}`;
    checkbox.className = 'line-item-checkbox';
    checkbox.addEventListener('change', (e) => {
        toggleLineItemBoundingBoxes(lineItemIndex, e.target.checked);
    });
    
    const checkboxLabel = document.createElement('label');
    checkboxLabel.htmlFor = `line-item-checkbox-${lineItemIndex}`;
    checkboxLabel.className = 'line-item-checkbox-label';
    checkboxLabel.textContent = 'Show on PDF';
    
    checkboxWrapper.appendChild(checkbox);
    checkboxWrapper.appendChild(checkboxLabel);
    
    const numberSpan = document.createElement('span');
    numberSpan.className = 'line-item-number';
    numberSpan.textContent = `Line Item #${index}`;
    
    const rightSection = document.createElement('div');
    rightSection.className = 'line-item-header-right';
    
    const badgeSpan = document.createElement('span');
    badgeSpan.className = 'line-type-badge';
    const lineType = typeof item.lineTypeSectionTotalItem === 'object' 
        ? item.lineTypeSectionTotalItem.value 
        : item.lineTypeSectionTotalItem;
    if (lineType === 'ITEM') {
        badgeSpan.classList.add('item');
        badgeSpan.textContent = 'Item';
    } else if (lineType === 'SECTION TOTAL') {
        badgeSpan.classList.add('section-total');
        badgeSpan.textContent = 'Section Total';
    } else {
        badgeSpan.textContent = 'Unknown';
    }
    
    rightSection.appendChild(badgeSpan);
    
    headerDiv.appendChild(checkboxWrapper);
    headerDiv.appendChild(numberSpan);
    headerDiv.appendChild(rightSection);
    
    // Tag grid
    const tagGridDiv = document.createElement('div');
    tagGridDiv.className = 'tag-grid';
    
    // Add all tags
    Object.keys(tagLabels).forEach(key => {
        if (item.hasOwnProperty(key)) {
            const tagItem = createTagElement(tagLabels[key], item[key]);
            tagGridDiv.appendChild(tagItem);
        }
    });
    
    lineItemDiv.appendChild(headerDiv);
    lineItemDiv.appendChild(tagGridDiv);
    
    return lineItemDiv;
}

function createTagElement(label, fieldData) {
    const tagDiv = document.createElement('div');
    tagDiv.className = 'tag-item';
    
    const labelDiv = document.createElement('div');
    labelDiv.className = 'tag-label';
    labelDiv.textContent = label;
    
    const valueDiv = document.createElement('div');
    valueDiv.className = 'tag-value';
    
    // Handle new structure (object with value, labelBbox, valueBbox)
    let value = '';
    if (typeof fieldData === 'object' && fieldData !== null) {
        value = fieldData.value || '';
    } else {
        value = fieldData || '';
    }
    
    if (!value || value.trim() === '') {
        valueDiv.classList.add('empty');
        valueDiv.textContent = 'Not available';
    } else {
        valueDiv.textContent = value;
    }
    
    tagDiv.appendChild(labelDiv);
    tagDiv.appendChild(valueDiv);
    
    return tagDiv;
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.add('show');
}

function hideError() {
    errorMessage.classList.remove('show');
}

