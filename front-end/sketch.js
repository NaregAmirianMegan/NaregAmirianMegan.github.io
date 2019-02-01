const dots = [];
const numDots = 200;
const WIDTH = window.innerWidth;
const HEIGHT = window.innerHeight;

function setup() {
  const cnv = createCanvas(WIDTH, HEIGHT);
  cnv.mouseClicked(onClick);
  for(let i = 0; i < numDots;i++) {
    dots.push(new Dot(random(WIDTH), random(HEIGHT)));
  }
}

function onClick() {
  dots.push(new Dot(mouseX, mouseY));
  numDots++;
}

function keyPressed() {
  if(keyCode === ENTER) {
    const input = document.getElementById('searchBox').value;
    document.getElementById("output").innerHTML = input;
  }
  for(let dot of dots) {
    dot.pressed = true;
  }
}

function draw() {
  background(0);
  for(let dot of dots) {
    for(let otherDot of dots) {
      if(otherDot !== dot) {
        if(distance(dot, otherDot) < 100) {
          stroke(255);
          line(dot.x, dot.y, otherDot.x, otherDot.y);
        }
      }
    }
    dot.show();
    dot.pressed = false;
  }
}

function distance(a, b) {
  return Math.sqrt(Math.pow(a.x - b.x, 2) + Math.pow(a.y - b.y, 2));
}
