"""Vector hardware symbols and orthogonal typed nets for LeNet diagrams.

These are authored diagrams of the implementation, not vendor-tool screenshots.
"""

from pathlib import Path
import math

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import Rectangle, Circle, Polygon, PathPatch, FancyArrowPatch


BLACK='#17212A'
CONTROL='#A65E13'
GRAY='#63717D'
BLUE='#1D566E'


class Circuit:
    def __init__(self,title,subtitle='',w=16,h=8):
        self.fig,self.ax=plt.subplots(figsize=(w,h))
        self.fig.subplots_adjust(left=.025,right=.975,top=.98,bottom=.035)
        self.w,self.h=w,h
        self.ax.set(xlim=(0,w),ylim=(0,h));self.ax.axis('off')
        self.fig.patch.set_facecolor('white')
        self.nets=[]
        self.junctions=[]
        self.bodies=[]
        plt.rcParams['svg.fonttype']='none'
        self.text(w/2,h-.35,title,16,bold=True)
        if subtitle:self.text(w/2,h-.77,subtitle,9.2,color=GRAY)

    def text(self,x,y,s,size=9,ha='center',va='center',color=BLACK,bold=False,rotation=0,back=False):
        return self.ax.text(x,y,s,fontsize=size,ha=ha,va=va,color=color,
                            fontweight='bold' if bold else 'normal',rotation=rotation,zorder=12,
                            bbox={'facecolor':'white','edgecolor':'none','pad':.7} if back else None)

    def wire(self,points,bits=None,label='',control=False,arrow=True,at=None):
        """Orthogonal signal net, with its arrow tip precisely on the sink pin.

        Trunk buses, timing guides and selector pin stubs explicitly opt out of
        arrows. Width ticks are projected onto a real segment of the net.
        """
        routed=[tuple(points[0])]
        for point in points[1:]:
            point=tuple(point);old=routed[-1]
            if math.dist(old,point)<1e-7:continue
            if abs(old[0]-point[0])>1e-7 and abs(old[1]-point[1])>1e-7:
                routed.append((old[0],point[1]))
            routed.append(point)
        points=routed
        if len(points)<2:return
        color=CONTROL if control else BLACK
        width=1.1 if control else (1.85 if bits and bits>1 else 1.4)
        style='--' if control else '-'
        self.ax.plot([p[0] for p in points],[p[1] for p in points],color=color,lw=width,ls=style,
                     solid_capstyle='butt',solid_joinstyle='miter',zorder=2)
        self.nets.append({'points':points,'color':color,'width':width,'style':style})
        if arrow:
            a,b=next(((a,b) for a,b in reversed(list(zip(points,points[1:]))) if math.dist(a,b)>.055),
                     (points[-2],points[-1]))
            length=math.dist(a,b);ux=(b[0]-a[0])/length;uy=(b[1]-a[1])/length
            head=min(.135 if not control else .115,length*.42)
            half=head*.43;tx,ty=points[-1]
            self.ax.add_patch(Polygon([(tx,ty),(tx-head*ux-half*uy,ty-head*uy+half*ux),
                                      (tx-head*ux+half*uy,ty-head*uy-half*ux)],
                                     facecolor=color,edgecolor=color,lw=.45,zorder=10))
        segments=[(a,b) for a,b in zip(points,points[1:]) if math.dist(a,b)>.22]
        if not segments:segments=list(zip(points,points[1:]))
        if at is None:
            a,b=max(segments,key=lambda pair:math.dist(*pair))
            at=((a[0]+b[0])/2,(a[1]+b[1])/2)
        def project(segment):
            a,b=segment;dx=b[0]-a[0];dy=b[1]-a[1];den=dx*dx+dy*dy
            t=max(.12,min(.88,((at[0]-a[0])*dx+(at[1]-a[1])*dy)/den))
            p=(a[0]+t*dx,a[1]+t*dy)
            return math.dist(p,at),p,abs(dx)<1e-7
        _,at,vertical=min((project(segment) for segment in segments),key=lambda row:row[0])
        if bits and bits>1:
            x,y=at
            self.ax.plot([x-.045,x+.045],[y-.09,y+.09],color=color,lw=1.0,zorder=9)
            self.text(x+.08,y+.15,str(bits),7.7,ha='left',color=color,back=True)
        if label:
            if vertical:self.text(at[0]-.15,at[1],label,8.1,color=color,rotation=90,back=True)
            else:self.text(at[0],at[1]+.28,label,8.4,color=color,back=True)

    def dot(self,x,y):
        self.junctions.append((x,y))
        self.ax.add_patch(Circle((x,y),.042,facecolor=BLACK,edgecolor=BLACK,zorder=11))

    def _crossings(self):
        """Use a small white isolation gap at unconnected internal crossings."""
        segments=[]
        for net_id,net in enumerate(self.nets):
            for a,b in zip(net['points'],net['points'][1:]):
                segments.append((net_id,a,b,net))
        used=set()
        for i,(idx,a,b,net) in enumerate(segments):
            horizontal=abs(a[1]-b[1])<1e-7
            for old_id,u,v,old in segments[:i]:
                if old_id==idx or horizontal==(abs(u[1]-v[1])<1e-7):continue
                h0,h1,v0,v1=(a,b,u,v) if horizontal else (u,v,a,b)
                x,y=v0[0],h0[1]
                if not (min(h0[0],h1[0])+.12<x<max(h0[0],h1[0])-.12 and
                        min(v0[1],v1[1])+.12<y<max(v0[1],v1[1])-.12):continue
                if any(math.dist((x,y),p)<.14 for p in self.junctions):continue
                if any(bx-.04<x<bx+bw+.04 and by-.04<y<by+bh+.04 for bx,by,bw,bh in self.bodies):continue
                key=(round(x,4),round(y,4))
                if key in used:continue
                used.add(key)
                self.ax.add_patch(Circle((x,y),.075,facecolor='white',edgecolor='none',zorder=5))
                points=[(x-.105,y),(x+.105,y)] if horizontal else [(x,y-.105),(x,y+.105)]
                self.ax.plot([p[0] for p in points],[p[1] for p in points],color=net['color'],lw=net['width'],
                             ls=net['style'],solid_capstyle='butt',zorder=6)

    def block(self,x,y,w,h,label,sub='',clocked=False,fill='white',size=10):
        self.bodies.append((x,y,w,h))
        self.ax.add_patch(Rectangle((x,y),w,h,facecolor=fill,edgecolor=BLACK,lw=1.35,zorder=3))
        self.text(x+w/2,y+h*(.63 if sub else .5),label,size,bold=True)
        if sub:self.text(x+w/2,y+h*.26,sub,size-1,color=GRAY)
        if clocked:self.clock(x,y+.2)
        return {'L':(x,y+h/2),'R':(x+w,y+h/2),'T':(x+w/2,y+h),'B':(x+w/2,y)}

    def clock(self,x,y,mirror=False):
        direction=-1 if mirror else 1
        self.ax.add_patch(Polygon([(x,y-.09),(x+.14*direction,y),(x,y+.09)],
                                 closed=True,facecolor='white',edgecolor=BLACK,lw=1.0,zorder=5))
        self.text(x-.06*direction,y,'clk',6.6,ha='right' if not mirror else 'left',color=GRAY)

    def reg(self,x,y,w,h,label,bits,ce=None,rst='rst',mirror=False):
        self.bodies.append((x,y,w,h))
        self.ax.add_patch(Rectangle((x,y),w,h,facecolor='#F5F8FA',edgecolor=BLACK,lw=1.35,zorder=3))
        self.text(x+w/2,y+h*.65,label,9,bold=True)
        self.text(x+w/2,y+h*.34,f'{bits}b',8.2,color=GRAY)
        dx=x+w if mirror else x; qx=x if mirror else x+w
        self.clock(dx,y+.16,mirror)
        self.text(dx+(-.11 if mirror else .11),y+h/2,'D',6.6,ha='right' if mirror else 'left')
        self.text(qx+(.11 if mirror else -.11),y+h/2,'Q',6.6,ha='left' if mirror else 'right')
        if ce:self.text(x+w/2,y+h+.14,'CE='+ce,7.0,color=CONTROL)
        if rst:self.text(x+w/2,y-.13,'R='+rst,6.8,color=CONTROL)
        return {'D':(dx,y+h/2),'Q':(qx,y+h/2),'CE':(x+w/2,y+h),'R':(x+w/2,y)}

    def mem(self,x,y,w,h,label,rows,bits,depth,clocked=True):
        self.bodies.append((x,y,w,h))
        self.ax.add_patch(Rectangle((x,y),w,h,facecolor='#F6F6F2',edgecolor=BLACK,lw=1.35,zorder=3))
        self.text(x+w/2,y+h-.26,label,10,bold=True)
        self.text(x+w/2,y+h-.59,f'{depth:,} x {bits} bits',8.4,color=GRAY)
        for i,row in enumerate(rows):
            line=y+.38+i*.36
            if line<y+h-.78:
                self.ax.plot([x+.12,x+w-.12],[line-.16,line-.16],color='#A5ADB1',lw=.6,zorder=4)
                self.text(x+w/2,line,row,8.1)
        if clocked:self.clock(x,y+.18)
        return {'A':(x,y+h*.62),'EN':(x,y+h*.28),'Q':(x+w,y+h*.54),'T':(x+w/2,y+h),'B':(x+w/2,y)}

    def alu(self,x,y,symbol,r=.25):
        self.bodies.append((x-r,y-r,2*r,2*r))
        self.ax.add_patch(Circle((x,y),r,facecolor='white',edgecolor=BLACK,lw=1.4,zorder=4))
        self.text(x,y,symbol,14,bold=True)
        return {'L':(x-r,y),'R':(x+r,y),'T':(x,y+r),'B':(x,y-r)}

    def mux(self,x,y,w=.7,h=1.1,sel='sel'):
        self.bodies.append((x,y-h/2,w,h))
        self.ax.add_patch(Polygon([(x,y-h/2),(x+w,y-h*.3),(x+w,y+h*.3),(x,y+h/2)],
                                 closed=True,facecolor='white',edgecolor=BLACK,lw=1.35,zorder=4))
        self.text(x+.12,y-h*.23,'0',6.5)
        self.text(x+.12,y+h*.23,'1',6.5)
        bottom=(x+w*.55,y-h*.39)
        self.wire([(bottom[0],bottom[1]-.25),bottom],control=True)
        if sel:self.text(bottom[0],bottom[1]-.4,sel,7.2,color=CONTROL)
        return {'0':(x,y-h*.23),'1':(x,y+h*.23),'Q':(x+w,y),'S':bottom}

    def gate(self,x,y,kind='and',w=.8,h=.65):
        self.bodies.append((x,y-h/2,w,h))
        if kind=='and':
            vertices=[(x,y-h/2),(x+w*.45,y-h/2),(x+w*1.18,y-h/2),
                      (x+w*1.18,y+h/2),(x+w*.45,y+h/2),(x,y+h/2),(x,y-h/2)]
            codes=[PlotPath.MOVETO,PlotPath.LINETO,PlotPath.CURVE4,PlotPath.CURVE4,
                   PlotPath.CURVE4,PlotPath.LINETO,PlotPath.CLOSEPOLY]
            ins=[(x,y-h*.23),(x,y+h*.23)]
        else:
            vertices=[(x,y-h/2),(x+w*.65,y-h/2),(x+w*.9,y-h*.2),(x+w,y),
                      (x+w*.9,y+h*.2),(x+w*.65,y+h/2),(x,y+h/2),
                      (x+w*.25,y+h*.15),(x+w*.25,y-h*.15),(x,y-h/2)]
            codes=[PlotPath.MOVETO]+[PlotPath.CURVE4]*9
            ins=[(x+w*.16,y-h*.23),(x+w*.16,y+h*.23)]
        self.ax.add_patch(PathPatch(PlotPath(vertices,codes),facecolor='white',edgecolor=BLACK,lw=1.2,zorder=4))
        return {'a':ins[0],'b':ins[1],'Q':(x+w,y)}

    def inv(self,x,y,w=.55,h=.45):
        self.bodies.append((x,y-h/2,w,h))
        self.ax.add_patch(Polygon([(x,y-h/2),(x,y+h/2),(x+w*.75,y)],closed=True,
                                 facecolor='white',edgecolor=BLACK,lw=1.1,zorder=4))
        self.ax.add_patch(Circle((x+w*.86,y),w*.11,facecolor='white',edgecolor=BLACK,lw=1.0,zorder=4))
        return {'D':(x,y),'Q':(x+w,y)}

    def footer(self,source=''):
        self.text(self.w/2,.34,'Arrows: signal direction  |  Slash + number: bus width  |  Dot: connection; gap: crossing  |  Dashed orange: control',7.7,color=GRAY)
        if source:self.text(self.w/2,.10,'Matin Firoozbakht  |  @matinfirooz  |  '+source,7.2,color=GRAY)

    def save(self,root,relative):
        self._crossings()
        path=Path(root)/relative;path.parent.mkdir(parents=True,exist_ok=True)
        self.fig.savefig(path,dpi=180,bbox_inches='tight',facecolor='white')
        self.fig.savefig(path.with_suffix('.svg'),bbox_inches='tight',facecolor='white')
        plt.close(self.fig)
        return path


