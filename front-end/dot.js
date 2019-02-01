class Dot {
  constructor(xPos, yPos) {
    this.x = xPos;
    this.y = yPos;
    this.size = random(4, 12);
    this.acc = 2;
    this.pressed = false;
    this.color = {
      r: random(255),
      g: random(255),
      b: random(255)
    }
    this.deltaX = random(-2, 2);
    this.deltaY = random(-2, 2);
    this.timeStep = 0;
  }
  checkEdges() {
    if (this.x > width) {
      this.x = 0;
    } else if (this.x < 0) {
      this.x = width;
    }
    if (this.y > height) {
      this.y = 0;
    } else if (this.y < 0) {
      this.y = height;
    }
  }
  update() {
    if(this.pressed) {
      this.acc = 20;
    } else {
      this.acc = 2;
    }
    this.x += this.deltaX*this.acc;
    this.y += this.deltaY*this.acc;
  }
  show() {
    stroke(0);
    fill(this.color.r, this.color.g, this.color.b);
    this.checkEdges();
    this.update();
    ellipse(this.x, this.y, this.size, this.size);
  }
}
