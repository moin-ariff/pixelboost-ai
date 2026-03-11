// Mobile navbar toggle
const navToggle = document.getElementById('navToggle');
const navLinks  = document.getElementById('navLinks');

navToggle.addEventListener('click', () => {
  navLinks.classList.toggle('open');
});

// Close navbar when link clicked (mobile)
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', () => {
    navLinks.classList.remove('open');
  });
});

// Close navbar when clicking outside
document.addEventListener('click', (e) => {
  if (!navToggle.contains(e.target) && !navLinks.contains(e.target)) {
    navLinks.classList.remove('open');
  }
});

// Set active link based on current page
const currentPath = window.location.pathname;
document.querySelectorAll('.nav-link').forEach(link => {
  link.classList.remove('active');
  if (link.getAttribute('href') === currentPath) {
    link.classList.add('active');
  }
});