import numpy as np
import matplotlib.pyplot as plt
import functools
import random
import multiprocessing
import threading
import time
import sys
import cvxpy as cp


class Slice(object):
    """ Slice of an antenna. Simulates traffic that arrives each adist() and requests a file with sdist() size.

        Parameters
        ----------
        adist : function
            a no parameter function that returns the successive inter-arrival times of connections
        sdist : function
            a no parameter function that returns the successive sizes of the files to be transferred
        C : float
            Ressource allocated by the antenna for the slice
            
        N : int shared variable
            number of active users, starts at 0, increases after each active thread
        slice_type: Type of slice
        N_max: int
            maximum number of users

    """
    def __init__(self, id,  adist, sdist,Cs,N,N_max,Rmin,Rmax,gamma,files_sent):#the rate has to become the shared variable
        self.id = id    
        self.adist = adist
        self.sdist = sdist
        self.files_sent = files_sent
        
        #self.N.value=multiprocessing.Value('i',0)
        self.N=N

        self.user_list=[]
        self.event_list=[]
        self.network_event=multiprocessing.Event()
        self.done_users=[]
        
        #Data rate given by antenna
        self.Cs=Cs
        
        ##Slice characteristics
        self.Rmin=Rmin
        self.Rmax=Rmax
        self.N_max=N_max
        self.gamma=gamma



    def slice_user(self,id):
        """Simulation of a user connceting to the slice and requesting download
        """
        packet_size=self.sdist()
        self.N.value+=1
        print("Slice id :"+str(self.id)+" |\033[92m User "+str(id)+" joined\033[00m. Packet size to send : "+str(packet_size)+" Interrupting ongoing connections.")
        for i,event in enumerate(self.event_list):
            if(i!=id) and  not (i in self.done_users):
                event.set()
                time.sleep(0.15)
                event.clear()
                
        
        start_time=time.time()
        print("Slice id :"+str(self.id)+" | N is equal to : "+str(self.N.value))
        transmit=True

        while(transmit):
            try:
                
                #TODO add ressource usage
                user_rate=self.Cs.value/self.N.value
                print("Slice id :"+str(self.id)+" | User "+str(id)+ "  Rate is "+str(user_rate))

                try:
                    time_to_send=packet_size/user_rate
                except ZeroDivisionError:#If the slice hasnt been allocated ressources we set a very hight time wait
                    time_to_send=1000000

                #Redundency to insure good functionning
                if(time_to_send<0):
                    self.N.value=self.N.value-1
                    self.files_sent.value += 1
                    self.done_users.append(id)
                    transmit=False
                    print("Slice id :"+str(self.id)+" |\033[91m User "+str(id)+ " disconnected\033[00m")
                    break
                #######################################
               
                time.sleep(0.15)

                #Send file. Interrupt if event is activated
                start_time=time.time()
                self.event_list[id].wait(time_to_send)

                if(self.network_event.is_set()):
                    raise StopIteration()

                #If reallocation event was activated reallocate
                if(self.event_list[id].is_set()):
                    raise ConnectionAbortedError()

                self.N.value=self.N.value-1
                self.files_sent.value += 1
                self.done_users.append(id)
                transmit=False
                print("Slice id :"+str(self.id)+" |\033[91m User "+str(id)+ " disconnected\033[00m")
            except ConnectionAbortedError:
                #Change data rate and retransmit
                print("Slice id :"+str(self.id)+" |\033[94m REALLOCATING\033[00m for user "+str(id)+" with "+ str(self.N.value)+" users ")
                #Calculate size left
                time_remaining=time_to_send-time.time()+start_time
                packet_size=time_remaining*user_rate
                print("Slice id :"+str(self.id)+" | Remaining size for user "+str(id)+" : "+str(packet_size))
            except StopIteration:
                print("Slice id :"+str(self.id)+" |\033[94m REALLOCATING\033[00m for user "+str(id)+" with "+ str(self.N.value)+" users ")


        #Reallocate at disconnection
        for i,event in enumerate(self.event_list):
            if(i!=id) and  not (i in self.done_users):
                
                event.set()
                time.sleep(0.1)
                event.clear()
                

    def run(self,simulation_status,reslicing_event):
        """The generator function used in simulations.
        """
        print("\033[92m"+"Running "+str(self.id)+"\033[00m")
        counter=0
        
        while not simulation_status.is_set():
            # wait for next connection
            reslicing_event.wait(self.adist())

            if(reslicing_event.is_set()):
                #The network manager has resliced reallocate everything
                self.network_event.set()
                time.sleep(0.1)
                self.network_event.clear()
                    
            else:
                # create a new user and append to user list
                if(len(self.user_list)-len(self.done_users))<=self.N_max:
                    
                    self.user_list.append(threading.Thread(target=self.slice_user,args=(counter,),daemon=True))
                    self.event_list.append(threading.Event())
                    self.user_list[-1].start()

                    # increment user id
                    counter+=1


class Network:
    """Class defining the network and its slices

        Parameters
        ----------
        C: Central capacity of the network
        t: float
            Simulation time
        simulation_status: Event
            event announcing the end of the simulation when set
        resclicing_trigger: int
            0 for static
            1 for timed
        

    """
    def __init__(self,C,t,simulation_status,resclicing_trigger):
        self.simulation_time=t
        self.resclicing_trigger=resclicing_trigger

        self.C_value=C
        
        #Define the functions for data rates and interarrival rates
        self.adist=[functools.partial(random.expovariate, 1/2),functools.partial(random.expovariate, 1/1)]
        self.sdist=[functools.partial(random.expovariate, 1/35),functools.partial(random.expovariate, 1/1)]

        self.rmin_v=[0.1,1]
        self.rmax_v=[7,1.5]

        self.gamma_v=[0.3,0.7]
        self.N_cont=[self.gamma_v[0]*self.C_value/self.rmin_v[0],self.gamma_v[1]*self.C_value/self.rmin_v[1]]

        self.N=[multiprocessing.Value('i',0),multiprocessing.Value('i',0)]
        self.C_vector=[multiprocessing.Value('f',self.C_value*self.gamma_v[0]),multiprocessing.Value('f',self.C_value*self.gamma_v[1])]

        self.resclicing_event=multiprocessing.Event()

        self.files_sent=[multiprocessing.Value('i',0),multiprocessing.Value('i',0)]

        self.slice1= Slice( "\033[93m"+"Slice1"+"\033[00m", self.adist[0], self.sdist[0],self.C_vector[0],self.N[0],100,self.rmin_v[0],self.rmax_v[0],self.gamma_v[0],self.files_sent[0])
        self.slice2= Slice( "\033[96m"+"Slice2"+"\033[00m", self.adist[1], self.sdist[1],self.C_vector[1],self.N[1],100,self.rmin_v[1],self.rmax_v[1],self.gamma_v[1],self.files_sent[1])

        self.process1=multiprocessing.Process(target=self.slice1.run,args=(simulation_status,self.resclicing_event,),daemon=True)
        self.process2=multiprocessing.Process(target=self.slice2.run,args=(simulation_status,self.resclicing_event,),daemon=True)


        self.monitor_process=multiprocessing.Process(target=monitor,args=(self.C_vector[0],self.C_vector[1],self.N[0],self.N[1],self.rmin_v,self.rmax_v,simulation_status,self.simulation_time,self.resclicing_trigger,),daemon=False)
    
    

    def run(self):
        
        self.process1.start()
        self.process2.start()

        self.monitor_process.start()

        #? Static assignement
        #TODO add monitoring for graph generation
        if self.resclicing_trigger==0:
            time.sleep(self.simulation_time)
            

        #? Timed resclicing
        elif self.resclicing_trigger==1:
            
            while((time.time()-GLOBAL_START_TIME)<self.simulation_time):
                #Wait for timer
                time.sleep(self.simulation_time/10)

                #Retreive simulation variables
                Ns_now=[self.N[0].value,self.N[1].value]

                #Reslice
                #TODO activate reallocation list
                #? Case 1: maximum throuput
                if(np.dot(Ns_now,self.rmax_v)<=self.C_value):
                    for i in range(number_of_slices):
                        self.C_vector[i].value=Ns_now[i]*self.rmax_v[i]
                    print("\033[93m Network Manager |\033[00m\033[1m RESLICED using case 1 : C = ",[self.C_vector[i].value for i in range(number_of_slices)],"\033[00m")
                
                #? Case 2: Total congestion
                elif(np.dot(Ns_now,self.rmin_v)>self.C_value):
                    
                    Ns_min=[min(Ns_now[i], self.N_cont[i]) for i in range(number_of_slices)]
                    
                    if(np.dot(Ns_min,self.rmin_v)>=self.C_value):
                        for i in range(number_of_slices):
                            self.C_vector[i].value=self.C_value*(Ns_min[i]*self.rmin_v[i])/(np.dot(Ns_min,self.rmin_v))
                    else:
                        for i in range(number_of_slices):
                            print(type((self.C_value-np.dot(Ns_min, self.rmin_v))))
                            self.C_vector[i].value=(Ns_min[i]*self.rmin_v[i])+(self.C_value-np.dot(Ns_min, self.rmin_v))*((Ns_now[i]-Ns_min[i])*self.rmin_v[i])/(np.dot(np.subtract(Ns_now,Ns_min),self.rmin_v))
                    
                    print("\033[93m Network Manager |\033[00m\033[1m RESLICED using case 2 : C = ",[self.C_vector[i].value for i in range(number_of_slices)],"\033[00m")

                #? Case 3: Average number of users
                elif(np.dot(Ns_now,self.rmax_v)>self.C_value and np.dot(Ns_now,self.rmin_v)<=self.C_value):
                    result_of_op=solve_optimisation(Ns_now, self.N_cont, self.C_value, self.rmin_v, self.rmax_v)
                    for i in range(number_of_slices):
                        self.C_vector[i].value=result_of_op[i]
                    
                    print("\033[93m Network Manager |\033[00m\033[1m RESLICED using case 3 : C = ",[self.C_vector[i].value for i in range(number_of_slices)],"\033[00m")

                #Trigger reallocation after reslicing
                self.resclicing_event.set()
                time.sleep(0.1)
                self.resclicing_event.clear()
        
        #Activate end of simulation event
        simulation_status.set()
        
        try:
            self.process1.close()
        except:
            pass
        try:
            self.process2.close()
        except:
            pass

        print("\033[92m"+"Network simulation complete"+"\033[00m")

        print("Number of files sent : ",[self.files_sent[0].value,self.files_sent[1].value])


def monitor(c_1,c_2,n_1,n_2,rmin,rmax,simulation_status,simulation_time,simu_type):
        """Function monitoring the slices to generate graphs
        """
        init_time=time.time()
        time_list=[]
        rs1_list=[]
        rs2_list=[]
        n1_list=[]
        n2_list=[]
        #start time
        time.sleep(2)
        while not simulation_status.is_set():
            time_list.append(time.time()-init_time)
            n1_list.append(n_1.value)
            n2_list.append(n_2.value)
            try:
                rs1_list.append(c_1.value/n_1.value)
            except:
                rs1_list.append(None)
                pass
            try:
                rs2_list.append(c_2.value/n_2.value)
            except:
                rs2_list.append(None)
                pass
            time.sleep(0.05)

        print("")
        print("####### Printing graphs ########")
        print("")
        # Create figure and subplots
        fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, sharex=False)

        # Plot rs1_list on first subplot
        ax1.plot(time_list, rs1_list, color='blue')
        ax1.set_ylabel('Rs1')
        

        # Plot rs2_list on second subplot
        ax2.plot(time_list, rs2_list, color='red')
        ax2.set_ylabel('Rs2')
        

        # Plot n1_list on first subplot
        ax3.plot(time_list, n1_list, color='blue')
        ax3.set_ylabel('Ns1')
        

        # Plot n2_list on first subplot
        ax4.plot(time_list, n2_list, color='red')
        ax4.set_ylabel('Ns2')
        ax4.set_xlabel('time')

        #Plot Rsmin and Rsmax for each graph
        ax1.axhline(y=rmin[0], color='green', linestyle='-')
        ax1.axhline(y=rmax[0], color='orange', linestyle='-')
        ax2.axhline(y=rmin[1], color='green', linestyle='-')
        ax2.axhline(y=rmax[1], color='orange', linestyle='-')

        if(simu_type==1):
            #Draw vertical Axes for reslicing
            count=simulation_time/10
            for i in range(0,int(simulation_time),int(simulation_time/10)):
                ax1.axvline(x=i, color='yellow', linestyle='--')
                ax2.axvline(x=i, color='yellow', linestyle='--')
                ax3.axvline(x=i, color='yellow', linestyle='--')
                ax4.axvline(x=i, color='yellow', linestyle='--')

        # Show plot
        plt.show()


def solve_optimisation(Ns,Ncont,C,Rmin,Rmax):
    """Function for solving the allocation problem

        Parameters
        ----------
        Ns : vector of active user per slice
        Ncont : limit number of users ensuring performance isolation
        C : Available common capacity
        Rmin : minimum data rate per slice
        Rmax : maximum data rate per slice
    """

    #Define Variable to be resolved
        #The variable is Rs. Its a vector of size 2
    x=cp.Variable(2)
    
    #Construct the problem
    objective = cp.Maximize(cp.sum(np.multiply(W_func(Ns, Ncont),Ns)@x))
    constraints=[Ns@cp.transpose(x)==C,x<=Rmax,x>=Rmin]
    prob = cp.Problem(objective=objective,constraints=constraints)
    
    #Solve the porblem
    prob.solve()

    #Return the value
    return np.multiply(x.value,Ns)

def W_func(Ns,Ncont):
    """W function defined in the paper
    
        Parameters
        ----------
        Ncont: array of maximum number of active users per slice
        Ns : array number of active users in the slice
    """
    assert len(Ns)==len(Ncont)==number_of_slices
    result=[]
    for i in range(len(Ns)):
        if(Ns[i]<=Ncont[i]):
            result.append(1)
        else:
            result.append(Ncont[i]/Ns[i])
    return result
    

if __name__ == '__main__':
    print("#####################################################")
    print("############# Starting Slicing Simulator ############")
    print("#####################################################")
    print("")

    if len(sys.argv)!=3:
        raise AttributeError("Input <simulation_time> <type_of_reclicing_trigger>")
    try:
        simulation_time=int(sys.argv[1])
    except TypeError:
        raise TypeError("<simulation_time> has to be an integer")
    try:
        resclicing_trigger=int(sys.argv[2])
    except TypeError:
        raise TypeError("<type_of_reclicing_trigger> has to be an integer")
    
    if resclicing_trigger!=0 and resclicing_trigger!=1:
        raise ValueError("<type_of_reclicing_trigger> can only be 0 (static) or 1 (timed)")
    

    simulation_status=multiprocessing.Event()
    net=Network(20,simulation_time,simulation_status,resclicing_trigger)
    GLOBAL_START_TIME=time.time()
    number_of_slices=2
    net.run()
    