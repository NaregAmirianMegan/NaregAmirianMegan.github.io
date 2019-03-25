const dots = [];
const numDots = 90;
const WIDTH = window.innerWidth;
const HEIGHT = window.innerHeight;

function setup() {
  const cnv = createCanvas(WIDTH, HEIGHT);
  cnv.position(0, 0);
  cnv.style('z-index', '-1');
  for(let i = 0; i < numDots;i++) {
    dots.push(new Dot(random(WIDTH), random(HEIGHT)));
  }
}

function draw() {
  background(0);
  for(let dot of dots) {
    for(let otherDot of dots) {
      if(otherDot !== dot) {
        if(distance(dot, otherDot) < 150) {
          stroke(134, 33, 33);
          line(dot.x, dot.y, otherDot.x, otherDot.y);
        }
      }
    }
    dot.show();
  }
}

function distance(a, b) {
  return Math.sqrt(Math.pow(a.x - b.x, 2) + Math.pow(a.y - b.y, 2));
}
