// DOM Elements
const discoveryForm = document.getElementById('discoveryForm');
const submitBtn = document.getElementById('submitBtn');
const loadingState = document.getElementById('loadingState');
const resultsSection = document.getElementById('resultsSection');
const errorSection = document.getElementById('errorSection');
const resultsSummary = document.getElementById('resultsSummary');
const parameterDetails = document.getElementById('parameterDetails');
const parameterList = document.getElementById('parameterList');
const downloadLink = document.getElementById('downloadLink');
const errorMessage = document.getElementById('errorMessage');
const urlError = document.getElementById('urlError');
const urlErrorText = document.getElementById('urlErrorText');
const fileError = document.getElementById('fileError');
const fileErrorText = document.getElementById('fileErrorText');

// Backend API URL
const API_BASE_URL = 'http://127.0.0.1:8000';

// Validation functions
function validateUrl(url) {
    if (!url || url.trim() === '') {
        return { valid: false, message: 'API URL is required' };
    }
    
    const trimmedUrl = url.trim();
    const urlPattern = /^https?:\/\/.+/;
    
    if (!urlPattern.test(trimmedUrl)) {
        return { valid: false, message: 'URL must start with http:// or https://' };
    }
    
    return { valid: true, message: '' };
}

function validateFile(file) {
    if (!file) return { valid: true, message: '' }; // File is optional
    
    const allowedTypes = ['.json', '.yaml', '.yml'];
    const fileName = file.name.toLowerCase();
    const hasValidExtension = allowedTypes.some(ext => fileName.endsWith(ext));
    
    if (!hasValidExtension) {
        return { 
            valid: false, 
            message: 'File must be .json, .yaml, or .yml format' 
        };
    }
    
    return { valid: true, message: '' };
}

// Show validation errors
function showUrlError(message) {
    urlErrorText.textContent = message;
    urlError.classList.remove('hidden');
    document.getElementById('apiUrl').classList.add('border-red-500');
}

function showFileError(message) {
    fileErrorText.textContent = message;
    fileError.classList.remove('hidden');
    document.getElementById('specFile').classList.add('border-red-500');
}

// Hide validation errors
function hideValidationErrors() {
    urlError.classList.add('hidden');
    fileError.classList.add('hidden');
    document.getElementById('apiUrl').classList.remove('border-red-500');
    document.getElementById('specFile').classList.remove('border-red-500');
}

// Hide all sections initially
function hideAllSections() {
    loadingState.classList.add('hidden');
    resultsSection.classList.add('hidden');
    errorSection.classList.add('hidden');
}

// Show loading state
function showLoading() {
    hideAllSections();
    loadingState.classList.remove('hidden');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Scanning...';
}

// Show results
function showResults(response) {
    hideAllSections();
    resultsSection.classList.remove('hidden');
    submitBtn.disabled = false;
    submitBtn.textContent = 'Discover Parameters';

    // Display summary with visual indicators
    const discoveredClass = response.discovered_params > 0 ? 'bg-blue-50' : 'bg-gray-50';
    const missingClass = response.missing_params > 0 ? 'bg-green-50' : 'bg-gray-50';
    const discoveredTextClass = response.discovered_params > 0 ? 'text-blue-900' : 'text-gray-900';
    const missingTextClass = response.missing_params > 0 ? 'text-green-900' : 'text-gray-900';
    
    resultsSummary.innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="${discoveredClass} p-4 rounded-lg border ${response.discovered_params > 0 ? 'border-blue-200' : 'border-gray-200'}">
                <div class="text-2xl font-bold ${discoveredTextClass}">${response.discovered_params}</div>
                <div class="text-sm ${response.discovered_params > 0 ? 'text-blue-700' : 'text-gray-700'}">Parameters Discovered</div>
            </div>
            <div class="${missingClass} p-4 rounded-lg border ${response.missing_params > 0 ? 'border-green-200' : 'border-gray-200'}">
                <div class="text-2xl font-bold ${missingTextClass}">${response.missing_params}</div>
                <div class="text-sm ${response.missing_params > 0 ? 'text-green-700' : 'text-gray-700'}">New Parameters Added</div>
            </div>
            <div class="bg-gray-50 p-4 rounded-lg border border-gray-200">
                <div class="text-lg font-medium text-gray-900">${response.message}</div>
            </div>
        </div>
    `;

    // Show parameter details section if there are results
    if (response.discovered_params > 0 || response.missing_params > 0) {
        parameterDetails.classList.remove('hidden');
        parameterList.innerHTML = `
            <div class="space-y-2">
                <div class="flex items-center">
                    <div class="w-3 h-3 bg-blue-500 rounded-full mr-2"></div>
                    <span class="text-sm text-gray-700">Parameters discovered by Arjun</span>
                </div>
                <div class="flex items-center">
                    <div class="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
                    <span class="text-sm text-gray-700">New parameters added to spec</span>
                </div>
                <div class="flex items-center">
                    <div class="w-3 h-3 bg-gray-400 rounded-full mr-2"></div>
                    <span class="text-sm text-gray-700">Parameters already existing in spec</span>
                </div>
            </div>
        `;
    } else {
        parameterDetails.classList.add('hidden');
    }

    // Create download link
    const downloadUrl = `${API_BASE_URL}/${response.filename}`;
    downloadLink.innerHTML = `
        <a 
            href="${downloadUrl}" 
            download="${response.filename.split('/').pop()}"
            class="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition-colors"
        >
            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
            </svg>
            Download Updated Spec
        </a>
        <p class="mt-2 text-sm text-gray-600">
            File: <code class="bg-gray-100 px-2 py-1 rounded">${response.filename}</code>
        </p>
        <div class="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
            <p class="text-sm text-yellow-800">
                <strong>Note:</strong> Review the downloaded spec before using in production. 
                Discovered parameters may need manual verification and documentation.
            </p>
        </div>
    `;
}

// Show error
function showError(message) {
    hideAllSections();
    errorSection.classList.remove('hidden');
    submitBtn.disabled = false;
    submitBtn.textContent = 'Discover Parameters';
    errorMessage.textContent = message;
}

// Handle form submission
discoveryForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Hide any previous errors
    hideValidationErrors();
    
    const url = document.getElementById('apiUrl').value.trim();
    const fileInput = document.getElementById('specFile');
    const file = fileInput.files[0];
    
    // Validate URL
    const urlValidation = validateUrl(url);
    if (!urlValidation.valid) {
        showUrlError(urlValidation.message);
        return;
    }
    
    // Validate file
    const fileValidation = validateFile(file);
    if (!fileValidation.valid) {
        showFileError(fileValidation.message);
        return;
    }
    
    const formData = new FormData();
    formData.append('url', url);
    
    if (file) {
        formData.append('file', file);
    }
    
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE_URL}/discover`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showResults(data);
        } else {
            showError(data.error || 'An error occurred during discovery');
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Failed to connect to backend. Please ensure backend server is running.');
    }
});

// Real-time validation
document.getElementById('apiUrl').addEventListener('input', (e) => {
    const url = e.target.value.trim();
    if (url) {
        const validation = validateUrl(url);
        if (validation.valid) {
            hideValidationErrors();
        } else {
            showUrlError(validation.message);
        }
    } else {
        hideValidationErrors();
    }
});

document.getElementById('specFile').addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        const validation = validateFile(file);
        if (validation.valid) {
            hideValidationErrors();
        } else {
            showFileError(validation.message);
        }
    } else {
        hideValidationErrors();
    }
});

// Reset form when inputs change to hide results
document.getElementById('apiUrl').addEventListener('input', () => {
    hideAllSections();
});

document.getElementById('specFile').addEventListener('change', () => {
    hideAllSections();
});
