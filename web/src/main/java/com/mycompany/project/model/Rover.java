package com.mycompany.project.model;

public class Rover {
	private String rname;
	private String rtype;
	private String rip;

	public String getRname() {
		return rname;
	}

	public void setRname(String rname) {
		this.rname = rname;
	}

	public String getRtype() {
		return rtype;
	}

	public void setRtype(String rtype) {
		this.rtype = rtype;
	}

	public String getRip() {
		return rip;
	}

	public void setRip(String rip) {
		this.rip = rip;
	}

	public int getRdistance() {
		return rdistance;
	}

	public void setRdistance(int rdistance) {
		this.rdistance = rdistance;
	}

	private int rdistance;
}
