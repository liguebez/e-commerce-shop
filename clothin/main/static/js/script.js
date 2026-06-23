const hamburgerBtn = document.getElementById('hamburger-btn');
const mainNavbar = document.getElementById('main-navbar');
if (hamburgerBtn && mainNavbar) {
    hamburgerBtn.addEventListener('click', () => {
        mainNavbar.classList.toggle('menu-open');
    });
}

const productContainers = [...document.querySelectorAll('.product-slider')];
const nxtBtn = [...document.querySelectorAll('.nxt-btn')];
const preBtn = [...document.querySelectorAll('.pre-btn')];

productContainers.forEach((item, i) => {
    let containerDimensions = item.getBoundingClientRect();
    let containerWidth = containerDimensions.width;

    nxtBtn[i].addEventListener('click', () => {
        item.scrollLeft += containerWidth;
    })

    preBtn[i].addEventListener('click', () => {
        item.scrollLeft -= containerWidth;
    })
})