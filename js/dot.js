class Dot {
  constructor(xPos, yPos) {
    this.x = xPos;
    this.y = yPos;
    this.size = random(2, 4);
    this.color = {
      r: 255,
      g: 255,
      b: 255,
      a: 90
    }
    this.deltaX = random(-1, 1);
    this.deltaY = random(-1, 1);
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
    this.x += this.deltaX;
    this.y += this.deltaY;
  }
  show() {
    stroke(this.color.r, this.color.g, this.color.b);
    fill(this.color.r, this.color.g, this.color.b, this.color.a);
    this.checkEdges();
    this.update();
    ellipse(this.x, this.y, this.size, this.size);
  }
}
